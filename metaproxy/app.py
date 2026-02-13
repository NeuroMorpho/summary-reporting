from flask import Flask
import requests
import requests_cache
import json
import time
from flask_cors import CORS
import mysql.connector
import config

app = Flask(__name__)
CORS(app)

requests_cache.install_cache('nmoapi-cache', backend='sqlite', expire_after=86400)

# Simple in-memory cache for database queries
_db_cache = {}
_db_cache_expiry = {}
DB_CACHE_TTL = 86400  # 24 hours in seconds


# Fields that should be fetched from MySQL database with their corresponding levels
DB_FIELDS = {
    'brain_region_1': ('brainRegion', 'brainRegion_neuron', 'brainRegionId', 'brainRegionLevel', 1),
    'brain_region_2': ('brainRegion', 'brainRegion_neuron', 'brainRegionId', 'brainRegionLevel', 2),
    'brain_region_3': ('brainRegion', 'brainRegion_neuron', 'brainRegionId', 'brainRegionLevel', 3),
    'cell_type_1': ('cellType', 'cellType_neuron', 'cellTypeId', 'cellTypeLevel', 1),
    'cell_type_2': ('cellType', 'cellType_neuron', 'cellTypeId', 'cellTypeLevel', 2),
    'cell_type_3': ('cellType', 'cellType_neuron', 'cellTypeId', 'cellTypeLevel', 3),
}


def make_db_request(field):
    """
    Fetches field values from MySQL database for brain_region and cell_type fields.
    Uses in-memory caching to avoid repeated database queries.
    """
    # Check cache first
    current_time = time.time()
    if field in _db_cache and field in _db_cache_expiry:
        if current_time < _db_cache_expiry[field]:
            return _db_cache[field]

    table, link_table, id_col, level_col, level = DB_FIELDS[field]

    try:
        mydb = mysql.connector.connect(
            host=config.dbhost,
            user=config.dbuser,
            passwd=config.dbpass,
            database=config.dbname,
            port=config.dbport
        )
        cursor = mydb.cursor()

        query = f"""
            SELECT DISTINCT t.name
            FROM {table} t
            JOIN {link_table} lt ON t.id = lt.{id_col}
            WHERE lt.{level_col} = %s
            ORDER BY t.name
        """
        cursor.execute(query, (level,))
        rows = cursor.fetchall()

        fields_list = [row[0] for row in rows]

        cursor.close()
        mydb.close()

        result = {
            "field_name": field,
            "fields": fields_list
        }

        # Store in cache
        _db_cache[field] = result
        _db_cache_expiry[field] = current_time + DB_CACHE_TTL

        return result
    except mysql.connector.Error as error:
        print(f"MySQL error for {field}: {error}")
        return {
            "field_name": field,
            "fields": [],
            "error": str(error)
        }


def makeapirequest(field):
    """
    Makes api request for non-database fields.
    """
    r = requests.get('https://neuromorpho.org/api/neuron/fields/{}'.format(field))

    result = json.loads(r.text)
    npages = result["page"]["totalPages"]
    if npages > 1:
        for ix in range(1, npages):
            r = requests.get('https://neuromorpho.org/api/neuron/fields/{}?page={}'.format(field, ix))
            nextresult = json.loads(r.text)
            result["fields"] = result["fields"] + nextresult["fields"]

    del result["page"]
    return result


@app.route('/')
def metaproxy():
    """
    Takes incoming request and returns fields
    """
    # Fields to fetch from API
    api_fields = ['species', 'gender', 'min_weight', 'max_weight', 'age_classification',
                  'min_age', 'max_age', 'domain', 'Physical_Integrity', 'attributes',
                  'protocol', 'experiment_condition', 'stain', 'slicing_thickness',
                  'slicing_direction', 'reconstruction_software', 'objective_type',
                  'magnification', 'archive', 'reference_pmid', 'original_format',
                  'deposition_date', 'upload_date']

    # Fields to fetch from database
    db_fields = ['brain_region_1', 'brain_region_2', 'brain_region_3',
                 'cell_type_1', 'cell_type_2', 'cell_type_3']

    metafields = {}

    # Fetch API fields
    for item in api_fields:
        metafields[item] = makeapirequest(item)

    # Fetch database fields
    for item in db_fields:
        metafields[item] = make_db_request(item)

    toreturn = json.dumps(metafields)
    return toreturn


@app.route('/clearcache')
def clearcache():
    """
    Clears both API and database caches
    """
    requests_cache.clear()
    _db_cache.clear()
    _db_cache_expiry.clear()
    return {"success": "cache cleared"}


if __name__ == '__main__':
    app.run()
