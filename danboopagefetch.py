import requests
import time
import multiprocessing
import orm
import conf

def process_source(source_name, posts_url=None, params=None, url_format=None):
    session = orm.Session()
    dontbreak = True
    while params['page'] < 5000 and dontbreak:
        response = requests.get(posts_url, params=params)

        if response.status_code == 421:
            time.sleep(60)
            continue
        elif response.status_code != 200:
            print "FACK GOT A %d CODE" % response.status_code
            break
        
        images = response.json()
        if not images:
            print "No images, done."
            break

        for image in images:
            if 'file_url' not in image:
                continue
            exists_query = session.query(
                orm.Image
            ).filter(
                orm.Image.remote_id == image['id'],
                orm.Image.source_name == source_name,
            ).exists()
            if session.query(exists_query).scalar():
                print "FOUND EXISTING POST"
                dontbreak = False
                break
            else:
                try:
                    if source_name==u'danbooru':
                        new_img, new_tags = orm.Image.from_danbooru_response(image, fork=False)
                    else:
                        new_img, new_tags = orm.Image.from_danbooru_response(
                            image, fork=True, fork_url_format=url_format, fork_name=source_name
                        )
                    if new_img:
                        new_img.source_name = source_name
                    else:
                        continue
                    session.merge(new_img)
                    for tag in new_tags:
                        session.merge(tag)
                    session.commit()
                except Exception as e:
                    import ipdb; ipdb.set_trace()
                
        params['page'] += 1

if __name__ == '__main__':
    for source_name, kwargs in conf.sources.items():
        process_source(source_name, **kwargs)