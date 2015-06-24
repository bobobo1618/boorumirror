def process_image(image_id, full_url, thumb_url, source_url):
    import requests
    import orm
    import boto
    import gcs_oauth2_boto_plugin
    import tempfile
    import mimetypes
    import conf
    from PIL import Image as pimage
    from PIL import ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    import imagehash
    from hashtest import hash_image

    session = orm.Session()

    gcs_oauth2_boto_plugin.SetFallbackClientIdAndSecret(conf.client_id, conf.client_secret)

    fullbucket = boto.storage_uri(conf.fullbucket, 'gs').get_bucket()
    thumbbucket = boto.storage_uri(conf.thumbbucket, 'gs').get_bucket()

    # Fetch images
    print "%d: Starting" % image_id
    response = requests.get(source_url, stream=True)
    if not response.status_code == 200:
        session.query(orm.Image).filter(orm.Image.id == image_id).update({'fetched': -1})
        session.commit()
        return

    fulltemp = tempfile.NamedTemporaryFile()
    thumbtemp = tempfile.NamedTemporaryFile()

    for block in response.iter_content(4096):
        fulltemp.write(block)
    fulltemp.seek(0)

    himg = pimage.open(fulltemp)
    ahash, phash, dhash = imagehash.average_hash(himg), imagehash.phash(himg), imagehash.dhash(himg)
    ahash, phash, dhash = int(str(ahash), base=16), int(str(phash), base=16), int(str(dhash), base=16)

    # Save images, make thumb
    himg.thumbnail((640, 640))
    himg.convert("RGB").save(thumbtemp, format='WebP')
    
    del himg

    if ahash >= 2**63:
        ahash -= 2**64

    if phash >= 2**63:
        phash -= 2**64

    if dhash >= 2**63:
        dhash -= 2**64

    # Upload
    fulltemp.seek(0)
    thumbtemp.seek(0)

    fullkey = fullbucket.new_key(full_url.split('/')[-1])
    thumbkey = thumbbucket.new_key(thumb_url.split('/')[-1])

    meta = {
        'Cache-Control': 'public, max-age=3600',
        'Content-Type': response.headers['content-type'],
    }

    fullkey.set_contents_from_file(fulltemp, headers=meta)
    print "%d: Uploaded full" % image_id

    meta['Content-Type'] = 'image/webp'
    thumbkey.set_contents_from_file(thumbtemp, headers=meta)
    print "%d: Uploaded thumb" % image_id

    try:
        bmbhash = hash_image(fulltemp.name)
        session.add(orm.Hash(name=u'bmbhash', value=bmbhash, image_id=image_id))
    except:
        pass

    session.add(orm.Hash(name=u'ahash', value=ahash, image_id=image_id))
    session.add(orm.Hash(name=u'phash', value=phash, image_id=image_id))
    session.add(orm.Hash(name=u'dhash', value=dhash, image_id=image_id))
    session.query(orm.Image).filter(orm.Image.id == image_id).update({
        'fetched': 1, 'size': int(response.headers['content-length'])
    })
    session.commit()
    fulltemp.close()
    thumbtemp.close()

def process_wrap(thing):
    try:
        process_image(*thing)
    except Exception as e:
        print "Failed " + str(thing)
        print e

def process_images():
    import multiprocessing
    import orm

    session = orm.Session()
    images = session.query(
        orm.Image.id,
        orm.Image.full_url,
        orm.Image.thumb_url,
        orm.Image.remote_url
    ).filter(
        orm.Image.fetched == 0,
        orm.Image.source_name.in_((u'awwnime', u'danbooru'))
    )
    #for image_id, full_url, thumb_url, source_url in images:
    #    process_image(image_id, full_url, thumb_url, source_url)
    pool = multiprocessing.Pool(10)
    pool.map(process_wrap, [thing for thing in images])

if __name__ == '__main__':
    process_images()
