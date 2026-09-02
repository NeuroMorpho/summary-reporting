import os

sshhost = os.environ.get('SSH_HOST', '')
sshport = int(os.environ.get('SSH_PORT', '22'))
sshusername = os.environ.get('SSH_USERNAME', '')
sshpass = os.environ.get('SSH_PASS', '')

dbhost = os.environ.get('DB_HOST', 'db')
dbuser = os.environ.get('DB_USER', '')
dbpass = os.environ.get('DB_PASS', '')
dbsel = os.environ.get('DB_NAME', 'NeuMO')
dbport = int(os.environ.get('DB_PORT', '3306'))
searchserviceurl = os.environ.get('SEARCH_SERVICE_URL', 'https://neuromorpho.org/search/')
