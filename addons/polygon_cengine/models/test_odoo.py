import xmlrpc.client

url = 'http://localhost:8069/xmlrpc/2/'
db = 'storeuae'
username = 'sunny@polygonstores.com'
password = 'odoo@123'

# Connect to Odoo using XML-RPC
common_proxy = xmlrpc.client.ServerProxy(url + 'common', allow_none=True)
object_proxy = xmlrpc.client.ServerProxy(url + 'object', allow_none=True)
uid = common_proxy.authenticate(db, username, password, {})

product_template = object_proxy.execute_kw(db, uid, password, 'product.template.attribute.line', 'search_read', [[['id', '=', '1']]])

print(product_template)