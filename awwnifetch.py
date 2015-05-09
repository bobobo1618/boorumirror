def process_image(image):
    import requests
    import rethinkdb as r
    import boto
    import gcs_oauth2_boto_plugin
    import tempfile 
    import mimetypes
    import conf
    
    from wand.image import Image
    gcs_oauth2_boto_plugin.SetFallbackClientIdAndSecret(conf.client_id, conf.client_secret)

    fullbucket = boto.storage_uri(conf.fullbucket, 'gs').get_bucket()
    thumbbucket = boto.storage_uri(conf.thumbbucket, 'gs').get_bucket()

    c = r.connect()
    db = r.db('redditbooru')

    image = db.table('images').get(image['id']).run(c)

    print "%s: Starting" % image['basename']
    response = requests.get(image['s3Url'], stream=True)
    if not response.status_code == 200:
        db.table('images').get(image['id']).update({'fetched': False}).run(c, durability='soft')
        return
    img = Image(file=response.raw)

    fulltemp = tempfile.TemporaryFile()
    thumbtemp = tempfile.TemporaryFile()

    img.save(fulltemp)
    
    img.transform(resize='640x640>')
    img.format = 'webp'
    img.save(thumbtemp)

    fulltemp.seek(0)
    thumbtemp.seek(0)

    fullkey = fullbucket.new_key('.'.join((image['basename'], image['type'])))
    thumbkey = thumbbucket.new_key('.'.join((image['basename'], '500', 'webp')))

    meta = {
        'Cache-Control': 'public, max-age=3600',
        'Content-Type': mimetypes.guess_type(image['cdnUrl'])[0],
    }

    fullkey.set_contents_from_file(fulltemp, headers=meta)
    print "%s: Uploaded full" % (image['basename'])

    meta['Content-Type'] = 'image/webp'
    thumbkey.set_contents_from_file(thumbtemp, headers=meta)
    print "%s: Uploaded thumb" % (image['basename'])

    db.table('images').get(image['id']).update({'fetched': True}).run(c, durability='soft')

def process_images():
    import multiprocessing
    import rethinkdb as r
    c = r.connect()
    images = r.db('redditbooru').table('images').order_by(index=r.desc('dateCreated')).filter(r.row.has_fields('fetched').not_()).pluck('id').run(c)

    pool = multiprocessing.Pool(10)
    pool.map(process_image, images)

if __name__ == '__main__':
    process_images()