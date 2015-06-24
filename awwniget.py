import orm
import requests
import urlparse
from datetime import datetime
from sqlalchemy.sql import exists

base = 'http://s3.amazonaws.com/cdn.awwni.me'

sources = requests.get("http://awwnime.redditbooru.com/sources/").json()

params = {'limit': 500}
#, 'sources': ','.join(source['value'] for source in sources)


session = orm.Session()

keep_going = True
while keep_going:
    new = requests.get("http://awwnime.redditbooru.com/images/", params=params).json()
    
    if new == None:
        print "DONE"
        break

    params['afterDate'] = new[-1]['dateCreated']
    
    for image in new:
        exists_query = session.query(
            orm.Image
        ).filter(
            orm.Image.remote_id == image['imageId'],
            orm.Image.set_id == image['externalId'],
            orm.Image.source_name == u'awwnime',
        ).exists()
        if session.query(exists_query).scalar():
            keep_going = False
            break
        else:
            new_img, new_tags = orm.Image.from_awwnime_response(image)
            for tag in new_tags:
                session.merge(tag)
            session.merge(new_img)
            session.commit()