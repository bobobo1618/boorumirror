import requests
import urlparse
import rethinkdb as r
from datetime import datetime

base = 'http://s3.amazonaws.com/cdn.awwni.me'

c = r.connect()
db = r.db('redditbooru')

sources = requests.get("http://awwnime.redditbooru.com/sources/").json()

db.table('sources').insert([
    {
        'id': source['value'],
        'name': source['name'],
        'title': source['title'],
    } for source in sources
]).run(c)

params = {'afterDate': 0, 'limit': 500, 'sources': ','.join(source['value'] for source in sources)}

while True:
    new = requests.get("http://awwnime.redditbooru.com/images/", params=params).json()
    
    if new == None:
        print "DONE"
        break

    params['afterDate'] = new[-1]['dateCreated']

    for image in new:
        cdnparse = urlparse.urlparse(image['cdnUrl'])
        image['s3Url'] = base + cdnparse.path
        image.pop('age')
        image['id'] = str(image['id'])
        image['keywords'] = image['keywords'].split()
        image['basename'] = cdnparse.path[1:].split('.')[0]
        image['dateCreated'] = r.epoch_time(image['dateCreated'])
        image.pop('thumb')
    
    results = db.table('images').insert(new).run(c)
    if results['errors']:
        print 'DONE'
        break

for image in db.table('images').filter(not r.row.has_fields('size')).run(c):
    res = requests.head(image['s3Url'])
    if res.status_code == 200:
        db.table('images').get(image['id']).update({
            'size': int(res.headers['content-length']),
            'contentType': res.headers['content-type'],
        }).run(c, durability='soft', noreply=True)
    else:
        db.table('images').get(image['id']).update({
            'size': None,
            'contentType': None,
        }).run(c, durability='soft', noreply=True)
        print "No data for %s: %d" % (image['id'], res.status_code)