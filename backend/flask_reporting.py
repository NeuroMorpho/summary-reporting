import mysql.connector
import numpy as np
from flask import Flask
from flask import jsonify
from flask_cors import CORS, cross_origin
from flask import request
import json, requests, os
import threading
import time
import xml.etree.ElementTree as ET
import classNeuron
from flask import send_file
from copy import deepcopy
from zipfile import ZipFile
import csv
from logger import log
import config

app = Flask(__name__)
CORS(app)
# Set the database parameters to connect

neuron_ids = {}
global listOfGroupsNeuronInfo, listOfMorphoNeuronInfo, listOfPvecNeuronInfo, listOfFiles, dictGroupNeurons
listOfGroupsNeuronInfo = []
listOfMorphoNeuronInfo = []
listOfPvecNeuronInfo = []
listOfFiles = []
dictGroupNeurons = {}


@app.route('/', methods=['GET'])
def get():
    return "Summary Reporting Main Route"


@app.route('/checkdbconn/', methods=['GET'])
def check_db_connection():
    """Check database connection status for debugging."""
    try:
        mydb = mysql.connector.connect(
            host=config.dbhost,
            user=config.dbuser,
            passwd=config.dbpass,
            database=config.dbsel,
            port=config.dbport
        )
        cursor = mydb.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        mydb.close()
        return jsonify({
            "status": "connected",
            "host": config.dbhost,
            "database": config.dbsel,
            "port": config.dbport
        })
    except mysql.connector.Error as error:
        return jsonify({
            "status": "error",
            "host": config.dbhost,
            "database": config.dbsel,
            "port": config.dbport,
            "user": config.dbuser,
            "password": config.dbpass,
            "error": str(error)
        }), 500

FIELD_HIERARCHY = {
    'brain_region_2': ('brainRegion', 'brainRegion_neuron', 'brainRegionId', 'brainRegionLevel', 2, 1),
    'brain_region_3': ('brainRegion', 'brainRegion_neuron', 'brainRegionId', 'brainRegionLevel', 3, 2),
    'cell_type_2': ('cellType', 'cellType_neuron', 'cellTypeId', 'cellTypeLevel', 2, 1),
    'cell_type_3': ('cellType', 'cellType_neuron', 'cellTypeId', 'cellTypeLevel', 3, 2),
}

# The parent -> child map is small and near-static, but deriving it per request costs
# 6-50s of MySQL time (a broad parent such as cell type 'principal cell' matches over half
# the database). Build it once per field and serve the dropdowns from memory.
HIERARCHY_CACHE_TTL = 86400

_hierarchy_cache = {}
_hierarchy_cache_expiry = {}
_hierarchy_lock = threading.Lock()


def load_hierarchy(child_field):
    """Builds {parent_name: [child_name, ...]} for one child field."""
    table, link_table, id_col, level_col, child_level, parent_level = \
        FIELD_HIERARCHY[child_field]

    mydb = mysql.connector.connect(
        host=config.dbhost,
        user=config.dbuser,
        passwd=config.dbpass,
        database=config.dbsel,
        port=config.dbport
    )
    cursor = mydb.cursor()
    query = f"""
        SELECT DISTINCT parent_t.name, child_t.name
        FROM {link_table} parent_lt
        JOIN {table} parent_t
            ON parent_t.id = parent_lt.{id_col}
            AND parent_lt.{level_col} = %s
        JOIN {link_table} child_lt
            ON child_lt.neuronId = parent_lt.neuronId
            AND child_lt.{level_col} = %s
        JOIN {table} child_t
            ON child_t.id = child_lt.{id_col}
    """
    cursor.execute(query, (parent_level, child_level))

    hierarchy = {}
    for parent_name, child_name in cursor.fetchall():
        hierarchy.setdefault(parent_name, set()).add(child_name)

    cursor.close()
    mydb.close()

    return {parent: sorted(children) for parent, children in hierarchy.items()}


def get_hierarchy(child_field):
    with _hierarchy_lock:
        expiry = _hierarchy_cache_expiry.get(child_field, 0)
        if child_field not in _hierarchy_cache or time.time() > expiry:
            log.info('Loading hierarchy for ' + child_field)
            _hierarchy_cache[child_field] = load_hierarchy(child_field)
            _hierarchy_cache_expiry[child_field] = time.time() + HIERARCHY_CACHE_TTL
        return _hierarchy_cache[child_field]


def parse_parent_values(raw_values, known_parents):
    """Accepts repeated parent_values params, and comma-joined ones from older clients.
    A name that is itself a known parent is never split, so values containing a comma
    (e.g. 'type I (monopolar dendrites, multipolar axon)') survive the round trip."""
    parent_values = []
    for raw in raw_values:
        raw = raw.strip()
        if not raw:
            continue
        if raw in known_parents or ',' not in raw:
            parent_values.append(raw)
        else:
            parent_values.extend(v.strip() for v in raw.split(',') if v.strip())
    return parent_values


@app.route('/fields/<child_field>', methods=['GET'])
def get_filtered_fields(child_field):
    """Returns child field values filtered by parent selection."""
    if child_field not in FIELD_HIERARCHY:
        return jsonify({"field_name": child_field, "fields": [],
                        "error": "Unknown child field"})

    raw_values = request.args.getlist('parent_values')
    if not raw_values:
        return jsonify({"field_name": child_field, "fields": [],
                        "error": "parent_values required"})

    try:
        hierarchy = get_hierarchy(child_field)
    except mysql.connector.Error as error:
        print(f"MySQL error for filtered {child_field}: {error}")
        return jsonify({
            "field_name": child_field,
            "fields": [],
            "error": str(error)
        })

    parent_values = parse_parent_values(raw_values, hierarchy)
    if not parent_values:
        return jsonify({"field_name": child_field, "fields": []})

    fields = set()
    for parent in parent_values:
        fields.update(hierarchy.get(parent, []))

    return jsonify({
        "field_name": child_field,
        "fields": sorted(fields)
    })


# Neuron selection
#
# The search service indexes a single PMID per neuron, so a PMID filter sent there misses
# every neuron whose paper is listed second or later - and some neurons are indexed under
# the wrong paper altogether. neuron_article holds one row per neuron and paper, so PMID
# filters are resolved here and only the remaining filters go to the search service.

def pmid_neuron_ids(pmids):
    """Ids of the neurons linked to any of the given PMIDs (integers)."""
    if not pmids:
        return set()
    mydb = mysql.connector.connect(
        host=config.dbhost,
        user=config.dbuser,
        passwd=config.dbpass,
        database=config.dbsel,
        port=config.dbport
    )
    try:
        cursor = mydb.cursor()
        placeholders = ','.join(['%s'] * len(pmids))
        cursor.execute(
            f"SELECT DISTINCT neuron_id FROM neuron_article WHERE PMID IN ({placeholders})",
            tuple(pmids))
        return {row[0] for row in cursor.fetchall()}
    finally:
        mydb.close()


def search_service_neuron_ids(payload):
    response = requests.post(config.searchserviceurl + "metadata/neuronIds", json=payload)
    response.raise_for_status()
    return response.json()


def search_service_count(payload):
    response = requests.post(config.searchserviceurl + "metadata/count", json=payload)
    response.raise_for_status()
    return response.json()


def split_pmid_filter(payload):
    """Returns the PMID filter as integers and a copy of the payload without it.
    Values that are not integers are dropped."""
    rest = deepcopy(payload)
    pmids = []
    for value in rest.get('neuron', {}).pop('pmid', None) or []:
        try:
            pmids.append(int(value))
        except (TypeError, ValueError):
            continue
    return pmids, rest


def resolve_neuron_ids(payload):
    """Ids of the neurons matching a filter payload as built by the frontend."""
    pmids, rest = split_pmid_filter(payload)
    if not pmids:
        return [int(neuron_id) for neuron_id in search_service_neuron_ids(rest)]
    by_pmid = pmid_neuron_ids(pmids)
    if not rest.get('neuron'):
        return sorted(by_pmid)
    return [neuron_id for neuron_id in (int(i) for i in search_service_neuron_ids(rest))
            if neuron_id in by_pmid]


@app.route('/neuronIds', methods=['POST'])
def neuron_ids():
    return jsonify(resolve_neuron_ids(request.get_json(force=True)))


@app.route('/count', methods=['POST'])
def neuron_count():
    payload = request.get_json(force=True)
    pmids, rest = split_pmid_filter(payload)
    if not pmids:
        return jsonify(search_service_count(rest))
    return jsonify(len(resolve_neuron_ids(payload)))


#This method is responsible for sending back the final csv report file.
@app.route('/generateReport/download/<typeOfDat>', methods=['GET'])
def download_file(typeOfDat):
    log.info('Get Download File - Start')
    print("Download File: " + str(typeOfDat))
    parameters = typeOfDat.split("_")
    #typeOfReport = parameters[0]
    #timestamp = parameters[1]
    uploads = os.path.join(app.root_path, "reports")

    log.info('Get Download File - End')
    filePath = uploads + "/" + str(typeOfDat)
    return send_file(filePath)

#Driver method for generating reports.
@app.route('/generateReport',  methods=['GET'])
def get_reports_xls():
    global listOfGroupsNeuronInfo
    global listOfMorphoNeuronInfo
    global listOfPvecNeuronInfo
    log.info('Get Reports Csv - Start')
    #print(request.headers['payload'])
    payloadData = json.loads(request.headers['payload'])
    typeOfData = payloadData['typeOfData']
    fileName = payloadData['fileName']
    listOfGroupsNeuronInfo.clear()
    listOfMorphoNeuronInfo.clear()
    listOfPvecNeuronInfo.clear()
    listOfFiles.clear()
    getChunkedNeuronData(typeOfData, payloadData, fileName)
    result = {}
    workbookFile = ""
    if typeOfData == "Groups":
        workbookFile = generateGroupsXlsFile(fileName)
    elif typeOfData == "Morphometrics":
        workbookFile = generateMorphoXlsFile(fileName)
    elif typeOfData == "Persistence Vectors":
        workbookFile = generatePvecXlsFile(fileName)
    elif typeOfData == "All":
        workbookFile = generateZipFile(fileName)
    #print("File Created!")
    log.info('Get Reports Csv - End')

    result["filePath"] = workbookFile
    return jsonify(result)

#Splitting/Chunking the data for groups, morpho and pvec and adding the csv files to the list.
def getChunkedNeuronData(typeOfData, payload, fileName):
    log.info('Get Chunked Neuron Data - Start')
    neuronJsonData = resolve_neuron_ids(payload)
    neuronIdsLength = len(neuronJsonData)

    chunkSize = 20000
    count = 0
    global listOfGroupsNeuronInfo, listOfMorphoNeuronInfo, listOfPvecNeuronInfo
    global listOfFiles

    if(typeOfData == "All"):
        while(count < neuronIdsLength):
            tempChunk = neuronJsonData[count:chunkSize + count]
            getNeuronInfoForGroups(tempChunk)
            count = count + chunkSize
        
        count = 0
        while(count < neuronIdsLength):
            tempChunk = neuronJsonData[count:chunkSize + count]
            getNeuronInfoForMorpho(tempChunk)
            count = count + chunkSize
        
        count = 0
        while(count < neuronIdsLength):
            tempChunk = neuronJsonData[count:chunkSize + count]
            getNeuronInfoForPvecs(tempChunk)
            count = count + chunkSize
        
        listOfFiles.append(generateGroupsXlsFile(fileName))

        listOfFiles.append(generateMorphoXlsFile(fileName))

        listOfFiles.append(generatePvecXlsFile(fileName))
        listOfGroupsNeuronInfo.clear()
        listOfMorphoNeuronInfo.clear()
        listOfPvecNeuronInfo.clear()

    else:
        while(count < neuronIdsLength):
            tempChunk = neuronJsonData[count:chunkSize + count]
            if typeOfData == "Groups":
                getNeuronInfoForGroups(tempChunk)
            elif typeOfData == "Morphometrics":
                getNeuronInfoForMorpho(tempChunk)
            elif typeOfData == "Persistence Vectors":
                getNeuronInfoForPvecs(tempChunk)
            count = count + chunkSize
    
    log.info('Get Chunked Neuron Data - End')
    
#Driver method for retrieving groups.
def getNeuronInfoForGroups(tempChunk):
    sqlgetNeuronInfo(tempChunk, "Groups")

#Driver method for retrieving morpho and groups.
def getNeuronInfoForMorpho(tempChunk):
    global listOfGroupsNeuronInfo, dictGroupNeurons
    listOfGroupsNeuronInfo.clear()
    dictGroupNeurons.clear()
    sqlgetNeuronInfo(tempChunk, "Groups")
    neuronsList = generateNeuronGroupInfo()
    sqlgetNeuronInfo(tempChunk, "Morpho")

#Driver method for retrieving pvec and groups.
def getNeuronInfoForPvecs(tempChunk):
    global listOfGroupsNeuronInfo, dictGroupNeurons
    listOfGroupsNeuronInfo.clear()
    dictGroupNeurons.clear()
    sqlgetNeuronInfo(tempChunk, "Groups")
    neuronsList = generateNeuronGroupInfo()
    sqlgetNeuronInfo(tempChunk, "Pvec")

#Retrieve all the data with respect to groups, morpho and pvec based on the selction made.
def sqlgetNeuronInfo(listofIds, typeData):
    log.info('Get Neuron Info - Start')
    global listOfGroupsNeuronInfo
    global listOfMorphoNeuronInfo
    global listOfPvecNeuronInfo
    try:
        #mydb = mysql.connector.connect(host="localhost",user="root",passwd="password",database="nmdbDev")    
        mydb = mysql.connector.connect(host=config.dbhost, user=config.dbuser, passwd =config.dbpass, database=config.dbsel)
        cursor = mydb.cursor(dictionary=True)
        neuronFormatStrings = ','.join(['%s'] * len(listofIds))

        if typeData == "Groups":
            cursor.execute("""
            Select count(*) as numofNeurons, GROUP_CONCAT(CAST(neuron_name AS CHAR)) as neurons,archive_name,age_scale,gender,age_class,species,strain_name,
            stain,experiment_condition,protocol,slicing_direction,reconstruction_software,objective_type,original_format,
            magnification,min_age,max_age,min_weight,max_weight,note,slice_thickness,reference_pmid,shrinkage_reported,
            shrinkage_corrected,reported_value,reported_xy,reported_z,corrected_value,corrected_xy,corrected_z,
            brain_region,cell_type,reference_doi,physical_integrity,deposition_date,upload_date 
            from GenerateReport_Groups where neuron_id IN (%s) group by archive_name,age_scale,gender,age_class,
            species,strain_name,stain,experiment_condition,protocol,slicing_direction,
            reconstruction_software,objective_type,original_format,magnification,min_age,max_age,min_weight,
            max_weight,note,slice_thickness,reference_pmid,shrinkage_reported,shrinkage_corrected,reported_value,
            reported_xy,reported_z,corrected_value,corrected_xy,corrected_z,brain_region,cell_type,
            reference_doi,physical_integrity,deposition_date,upload_date""" % neuronFormatStrings, tuple(listofIds))
            neuronData = cursor.fetchall()
            for neuronRow in neuronData:
                listOfGroupsNeuronInfo.append(neuronRow)
            
        elif typeData == "Morpho":
            cursor.execute("Select * from measurements where neuron_id IN (%s)" % neuronFormatStrings, tuple(listofIds))
            neuronData = cursor.fetchall()
            for neuronRow in neuronData:
                listOfMorphoNeuronInfo.append(neuronRow)

        elif typeData == "Pvec":
            cursor.execute("Select *, ne.`neuron_name` from persistance_vector pv inner join neuron ne on ne.`neuron_id` = pv.`neuron_id` where pv.neuron_id IN (%s)" % neuronFormatStrings, tuple(listofIds))
            neuronData = cursor.fetchall()
            for neuronRow in neuronData:
                listOfPvecNeuronInfo.append(neuronRow)
        log.info('Get Neuron Info - End')

    except mysql.connector.Error as error:
        print("Failed to execute stored procedure: {}".format(error))

    finally:
        if (mydb.is_connected()):
            cursor.close()
            mydb.close()

#Helper method for stitching neuronids.
def convertToStringData(tempChunk): 
    neuronIdsString  = [str(neuronId) for neuronId in tempChunk]   
    res = str(",".join(neuronIdsString))   
    return(res) 

#Populate the list of neuron objects.
def generateNeuronGroupInfo():
    log.info('Generate Neuron Group Info - Start')
    neuronsList = []
    neuronObject = classNeuron.Neuron()
    neuronsCount = 0
    global dictGroupNeurons
    global listOfGroupsNeuronInfo
    for neuron in listOfGroupsNeuronInfo:
        neuronsCount = neuronsCount + 1
        neuronObject.numofNeurons = neuron["numofNeurons"]
        neuronObject.neurons = neuron["neurons"]
        neuronObject.archive = neuron["archive_name"]
        neuronObject.species = neuron["species"]
        neuronObject.strain = neuron["strain_name"]
        neuronObject.min_age = neuron["min_age"]
        neuronObject.max_age = neuron["max_age"]
        neuronObject.age_scale = neuron["age_scale"]
        neuronObject.min_weight = neuron["min_weight"]
        neuronObject.max_weight = neuron["max_weight"]
        neuronObject.note = neuron["note"]
        neuronObject.age_classification = neuron["age_class"]
        neuronObject.gender = neuron["gender"]
        neuronObject.brain_region = neuron["brain_region"]
        neuronObject.cell_type = neuron["cell_type"]
        neuronObject.original_format = neuron["original_format"]
        neuronObject.protocol = neuron["protocol"]
        neuronObject.slicing_thickness = neuron["slice_thickness"]
        neuronObject.slicing_direction = neuron["slicing_direction"]
        neuronObject.stain = neuron["stain"]
        neuronObject.magnification = neuron["magnification"]
        neuronObject.objective_type = neuron["objective_type"]
        neuronObject.reconstruction_software = neuron["reconstruction_software"]
        neuronObject.experiment_condition = neuron["experiment_condition"]
        neuronObject.deposition_date = neuron["deposition_date"]
        neuronObject.upload_date = neuron["upload_date"]
        neuronObject.reference_pmid = neuron["reference_pmid"]
        neuronObject.reference_doi = neuron["reference_doi"]
        neuronObject.shrinkage_reported = neuron["shrinkage_reported"]
        neuronObject.shrinkage_corrected = neuron["shrinkage_corrected"]
        neuronObject.reported_value = neuron["reported_value"]
        neuronObject.reported_xy = neuron["reported_xy"]
        neuronObject.reported_z = neuron["reported_z"]
        neuronObject.corrected_value = neuron["corrected_value"]
        neuronObject.corrected_xy = neuron["corrected_xy"]
        neuronObject.corrected_z = neuron["corrected_z"]
        neuronObject.physical_Integrity = neuron["physical_integrity"]

        neuronString = json.dumps(neuronObject.__dict__)
        neuronsList.append(neuronString)

        listOfSplitNeurons = str(neuron["neurons"]).split(',')
        #print(listOfSplitNeurons)
        for neuro in listOfSplitNeurons:
            dictGroupNeurons[neuro] = neuronsCount
    
    print('Group Neurons Length - ' + str(len(dictGroupNeurons)))
    log.info('Generate Neuron Group Info - End')
    return neuronsList
    

#Generates the group csv file based on the template stored in groupsCol for group.
def generateGroupsXlsFile(fileName):
    log.info('Generate Groups Excel File - Start')

    try:
        filePath = 'reports/' + 'groups_' + fileName + '.csv'
        listOfNeurons = []
        tree = ET.parse('groupsCol.xml')
        root = tree.getroot()
        nodes = root.findall('.//GroupCollection/Title')
        
        listOfNeurons = generateNeuronGroupInfo()
        
        csvDataDict = {}
        
        tempListOfNeurons = []
        tempListOfNeurons.append('Title')
        listOfNeuronsLength = len(listOfNeurons)
        for index in range(listOfNeuronsLength):
            tempListOfNeurons.append(str(index + 1))
        
        csvDataDict['Title'] = tempListOfNeurons

        for child in nodes:
            tempListOfNeurons = []
            tempListOfNeurons.append(str(child.attrib['name']))
            for neuronValue in listOfNeurons:
                neuronData = json.loads(neuronValue)
                tempListOfNeurons.append(str(neuronData[child.attrib['name']]))
            csvDataDict[child.attrib['name']] = tempListOfNeurons
            

        #print('Groups Process..')
        with open(filePath, 'w', newline='') as morpho_file:
            morpho_writer = csv.writer(morpho_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
            morpho_writer.writerow(csvDataDict['Title'])
            for childnode in nodes:
                morpho_writer.writerow(csvDataDict[childnode.attrib['name']])

        log.info('Generate Groups Excel File - End')
        #print("File Generated - Groups!!!")
        return filePath
    except Exception as ex:
        print(ex)

#Generates the morpho csv file based on the template stored in groupsCol for morpho.
def generateMorphoXlsFile(fileName):

    log.info('Generate Morpho Excel File - Start')
    try:
        filePath = 'reports/' + 'morpho_' + fileName + '.csv'
        tree = ET.parse('groupsCol.xml')
        root = tree.getroot()
        nodes = root.findall('.//MorphoCollection/Title')
        csvDataDict = {}
        global dictGroupNeurons
        global listOfMorphoNeuronInfo
        #print(dictGroupNeurons)
        for child in nodes:
            tempListOfNeurons = []
            tempListOfNeurons.append(str(child.attrib['name']))
            for rowData in listOfMorphoNeuronInfo:
                if str(child.attrib['name']) == "title":
                    #print(str(rowData['Neuron_name']))
                    if str(rowData['Neuron_name']) in dictGroupNeurons:
                        tempListOfNeurons.append(str(dictGroupNeurons[rowData['Neuron_name']]))
                    else:
                        tempListOfNeurons.append(str(0))
                else:
                    tempListOfNeurons.append(str(rowData[child.attrib['name']]))
            csvDataDict[child.attrib['name']] = tempListOfNeurons

        print('Morpho Process..')
        with open(filePath, 'w', newline='') as morpho_file:
            morpho_writer = csv.writer(morpho_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
            #morpho_writer.writerow(csvDataDict['Title'])
            for childnode in nodes:
                morpho_writer.writerow(csvDataDict[childnode.attrib['name']])
        
        #workbook.close()
        log.info('Generate Morpho Excel File - End')
        #print("File Generated - Morpho!!!")
        return filePath

    except Exception as ex:
        print(ex)

#Generates the pvec csv file based on the template stored in groupsCol for Pvec.
def generatePvecXlsFile(fileName):
    log.info('Generate Pvec Excel File - Start')
    try:
        filePath = 'reports/' + 'pvec_' + fileName + '.csv'
        tree = ET.parse('groupsCol.xml')
        root = tree.getroot()
        nodes = root.findall('.//PvecCollection/Title')
        fieldnames = []
        global dictGroupNeurons
        global listOfPvecNeuronInfo

        for child in nodes:
            fieldnames.append(child.attrib['name'])
    
        
        with open(filePath, 'w', newline='') as pvec_file:
            pvec_writer = csv.writer(pvec_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
            pvec_writer.writerow(fieldnames)
            tempGroup = 0
            for neuron in listOfPvecNeuronInfo:
                if str(neuron['neuron_name']) in dictGroupNeurons:
                    tempGroup = str(dictGroupNeurons[neuron['neuron_name']])
                else:
                    tempGroup = 0

                pvec_writer.writerow([str(tempGroup),neuron["neuron_id"], neuron["distance"], neuron["Sfactor"],neuron["coeff00"],neuron["coeff01"],neuron["coeff02"],
                neuron["coeff03"],neuron["coeff04"],neuron["coeff05"],neuron["coeff06"],neuron["coeff07"],neuron["coeff08"],neuron["coeff09"],neuron["coeff10"],
                neuron["coeff11"],neuron["coeff12"],neuron["coeff13"],neuron["coeff14"],neuron["coeff15"],neuron["coeff16"],neuron["coeff17"],neuron["coeff18"],
                neuron["coeff19"],neuron["coeff20"],neuron["coeff21"],neuron["coeff22"],neuron["coeff23"],neuron["coeff24"],neuron["coeff25"],neuron["coeff26"],
                neuron["coeff27"],neuron["coeff28"],neuron["coeff29"],neuron["coeff30"],neuron["coeff31"],neuron["coeff32"],neuron["coeff33"],neuron["coeff34"],
                neuron["coeff35"],neuron["coeff36"],neuron["coeff37"],neuron["coeff38"],neuron["coeff39"],neuron["coeff40"],neuron["coeff41"],neuron["coeff42"],
                neuron["coeff43"],neuron["coeff44"],neuron["coeff45"],neuron["coeff46"],neuron["coeff47"],neuron["coeff48"],neuron["coeff49"],neuron["coeff50"],
                neuron["coeff51"],neuron["coeff52"],neuron["coeff53"],neuron["coeff54"],neuron["coeff55"],neuron["coeff56"],neuron["coeff57"],neuron["coeff58"],
                neuron["coeff59"],neuron["coeff60"],neuron["coeff61"],neuron["coeff62"],neuron["coeff63"],neuron["coeff64"],neuron["coeff65"],neuron["coeff66"],
                neuron["coeff67"],neuron["coeff68"],neuron["coeff69"],neuron["coeff70"],neuron["coeff71"],neuron["coeff72"],neuron["coeff73"],neuron["coeff74"],
                neuron["coeff75"],neuron["coeff76"],neuron["coeff77"],neuron["coeff78"],neuron["coeff79"],neuron["coeff80"],neuron["coeff81"],neuron["coeff82"],
                neuron["coeff83"],neuron["coeff84"],neuron["coeff85"],neuron["coeff86"],neuron["coeff87"],neuron["coeff88"],neuron["coeff89"],neuron["coeff90"],
                neuron["coeff91"],neuron["coeff92"],neuron["coeff93"],neuron["coeff94"],neuron["coeff95"],neuron["coeff96"],neuron["coeff97"],neuron["coeff98"],neuron["coeff99"]])

        
        log.info('Generate Morpho Excel File - End')
        #print("File Generated - Pvec!!!")
        return filePath

    except Exception as ex:
        print(ex)

#Generates a zip file based on the selection made for the type of report.
def generateZipFile(fileName):
    log.info('Generate Zip File - Start')
    try:
        global listOfFiles
        zipPath = 'reports/' + 'all_' + fileName + '.zip'
        with ZipFile(zipPath,"w") as newzip:
            for filePath in listOfFiles:
                newzip.write(filePath)

        log.info('Generate Zip File - End')
        return zipPath
    

    except Exception as ex:
        print(ex)


