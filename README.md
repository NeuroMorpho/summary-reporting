Summary Reporting
=================
General description
-------------------
This tool may be accessed online at: http://cng.gmu.edu:8080/neuronMetadata/

Generates summary report based on the selection of the type of report: Neurons grouped by metadata, persistence vectors, or morphometrics. It is also possible to download all reports together in a zip file. 

Reports can be generated based on any combination of the following filters: Species, Gender, Minimum Weight, Maximum Weight, Development, Minimum Age, Maximum Age, Brain Regions, Cell Types, Structural Domain, Physical Integrity, Morphological Attributes, Protocol, Experiment Condition, Stain, Stain Thickness, Slicing Direction, Reconstruction Software, Objective Type, Objective Magnification, Archive, PMID, Original Format, Date of Deposition, and Date of Upload.

For further information, please see [link to published article]

Module descriptions and limitations of use
------------------------------------------
The application consists of the following modules, with descriptions and limitations of use after cloning and downloading of this repository as follows:
- **Frontend** - A static HTML page + dynamic javascript for the handling of UI events. The frontend/index.html file will provide a fully functional UI, see Installation below for further guidance. 
- **Metaproxy** - Python backend mini-module for generating and caching the menu choice selections as per the current metadata in NeuroMorpho. This module may be run as a standalone Docker image after downloading, please see Installation below for further guidance.
- **Backend** - This module fetches data from the API and the internal NeuroMorpho MySQL database. For security reasons, the database is NOT accessible for external use. This module thus cannot be run standalone if clone/downloaded; the source code is provided as-is for sake of transparency and as an example of possible interaction with the current API. We are developing a new API that will provide extended functionality of both the backend and the frontend also to a machine user. Currently, the interface is intended for a human user. 

Limitations of use
------------------
Please note that the software as a whole is not intended to run standalone. However, it serves as an example of how the API can be utilized and provided for transparency of the Summary reporting module. The backend currently interacts with the NeuroMorpho SQL database directly. Such interaction is currently not possible for external use.   However, after cloning this repository to a folder, the frontend/index.html will provide a fully functional UI (see Installation below). The UI may also be accessed at http://cng.gmu.edu:8080/neuronMetadata/ 

Installation
------------
Please note the Limitations of use above. The UI and the metaproxy may after cloning or downloading be installed and run independently:
- UI -- open the frontend/index.html file in a browser. If installing the Metaproxy backend, the frontend/main.js file must be updated with the new URL for it to run locally.
- Metaproxy 
    - Prerequisites: Docker[https;//docker.com] must be installed. 
    - Build docker image by switching directory from the base directory: `cd metaproxy` and then build image `docker build . -t metaproxy. If you are not using other Docker containers with Ubuntu, you may consider switching from Ubuntu to Alpine for space considerations.
    - Run docker image `docker run -p 5000:5000 -d metaproxy`
    - For a faster load of UI, the metaproxy may be precached by accessing the URL http://localhost:5000/. This usually takes 20-30s. The same URL may then be accessed for the meta data terms.
- Backend -- can NOT be installed and run standalone, for reasons described above.

Contributions
-------------
- Research and requirements: Masood Akram, Giorgio Ascoli
- System development: Navy Merianda, Praveen Menon, Bengt Ljungquist
- Project management and deployment: Bengt Ljungquist
