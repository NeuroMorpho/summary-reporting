import logging

log = logging.getLogger('flaskreporting')
hdlr = logging.FileHandler('flaskreporting.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr) 
log.setLevel(logging.INFO)
