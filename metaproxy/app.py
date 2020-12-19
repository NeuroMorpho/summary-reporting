from flask import Flask
import requests
import requests_cache
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

requests_cache.install_cache('nmoapi-cache', backend='sqlite', expire_after=86400)



def makeapirequest(field):
    """
    Makes api request 
    """
    r = requests.get('http://neuromorpho.org/api/neuron/fields/{}'.format(field))
    
    result = json.loads(r.text)
    npages = result["page"]["totalPages"]
    if npages > 1:
        for ix in range(1,npages):
            r = requests.get('http://neuromorpho.org/api/neuron/fields/{}?page={}'.format(field,ix))
            nextresult = json.loads(r.text)
            result["fields"] = result["fields"] + nextresult["fields"]

    del result["page"]
    return result


@app.route('/')
def metaproxy():
    """
    Takes incoming request and returns fields
    """
    fields = ['species','gender','min_weight','max_weight','age_classification','min_age','max_age','domain','Physical_Integrity','attributes','protocol','experiment_condition','stain','slicing_thickness','slicing_direction','reconstruction_software','objective_type','magnification','archive','reference_pmid','original_format','deposition_date','upload_date','brain_region_1','brain_region_2','brain_region_3','cell_type_1','cell_type_2','cell_type_3']
    metafields = {}
    
    for item in fields:
        metafields[item] = makeapirequest(item)

    toreturn = json.dumps(metafields)
    return toreturn


@app.route('/clearcache')
def clearcache():
    """
    Clears the cache
    """
    requests_cache.clear()
    return {"success": "cache cleared"}


if __name__ == '__main__':
    app.run()
