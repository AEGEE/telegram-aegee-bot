import xmlrpc.client

s = xmlrpc.client.ServerProxy('http://localhost:9000')

s.shutdown()