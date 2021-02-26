Summary Reporting
=================
General description
-------------------
Generates reports based on the selection of type of report: Groups, Morpho and Pvec.

Reports can be generated based on the filters listed below:

Species, Gender, Minimum Weight, Maximum Weight, Development, Minimum Age, Maximum Age, Brain Regions, Cell Types, Structural Domain,
Physical Integrity, Morphological Attributes, Protocol, Experiment Condition, Stain, Stain Thickness, Slicing Direction, Reconstruction Software,
Objective Type, Objective Magnification, Archive, PMID, Original Format, Date of Deposition, Date of Upload.

Reports can be downloaded either as grouped neurons, morpho attributes, persistance vectors or all of it together in a zip file.
Module descriptions and limitations of use
------------------------------------------
The application consists of the following modules, with descriptions and limitations of use after cloning and downloading of this reposityory as follows:
- **Frontend** - A static html page + dynamic javascript for handling of UI events. The frontend/index.html will provide a fully functional UI, see Installation below for further guidance. 
- **Metaproxy** - Python backend mini-module for generating and caching the menu choice selections as per the current metadata in NeuroMorpho. This module may be run as a standalone docker image after downloading, please see Installation below for further guidance.
- **Backend** - This module fetches data from the API and the internal NeuroMorpho MySQL database. For security reasons, the database is NOT accessible for external use. This module thus cannot be run standalone if clone/downloaded; the source code is provided as is for sake of transparency and as example of possible interaction with the current API. We are developing a new API which will provide extended functionality of both the backend and the frontend also to a machine user. Currently, the interface is intended for a human user. 

Limitations of use
------------------
Please note that the software as a whole, it is not intended to run standalone. However, it serves as an example of how the API can be utilized and provided for transparency of the Summary reporting module. The backend currently interacts with the NeuroMorpho SQL database directly. Such interaction is currently not possible for external use.   However, after cloning this reposityory to a folder, the frontend/index.html will provide a fully functional UI (see Installation below). The UI may also be accessed at http://cng.gmu.edu:8080/neuronMetadata/ 

Installation
------------
Plase note the Limitations of use above. The UI and the metaproxy may after cloning or downloading be viewed respectively started:
- UI -- open the frontend/index.html file in a browser. If installing the Metaproxy backend, the frontend/main.js file must be updated with the new URL for it to run locally.
- Metaproxy 
    - Prerequisites: Docker[https;//docker.com] must be installed. 
    - Build docker image by switching directory from base: `cd metaproxy` and then build image `docker build . -t metaproxy. If you are not using other containers with ubuntu, you may consider switching from ubuntu to alpine for space considerations.
    - Run docker image `docker run -p 5000:5000 -d metaproxy`
    - For faster load of UI, the metaproxy may be precached by accessing the url http://localhost:5000/. This usually takes 20-30s. The same url may then be accessed for the meta data terms.
- Backend -- can NOT be installed and run standalone, for reasons described above.

Contributions
-------------
- Research and requirements: Masood Akram, Giorgio Ascoli
- System development: Navy Merianda, Praveen Menon, Bengt Ljungquist
- Project management and deployment: Bengt Ljungquist