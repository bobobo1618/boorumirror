def process_id(externalid):
    #import requests
    import rethinkdb as r
    import conf
    import re
    import praw
    from lxml import html
    from praw.handlers import MultiprocessHandler
    handler = MultiprocessHandler()
    reddit = praw.Reddit(user_agent = conf.user_agent, handler=handler)

    sourceregex = re.compile(r'\[Source\]\((.*)\)')

    print "%s: Searching for source" % externalid
    submission = reddit.get_submission(submission_id=externalid)

    sourceUrl = ''

    for comment in submission.comments:
        tree = html.fromstring(html.fromstring(comment.body_html).text)
        matches = tree.xpath('//a[contains(text(), "Source")]')
        if matches:
            sourceUrl = matches[0].attrib['href']
            print "%s: Found source - %s" % (externalid, sourceUrl)

    c = r.connect()
    db = r.db('redditbooru')

    db.table('images').filter({'externalId': externalid}).update({'sourceUrl': sourceUrl or False}).run(c, durability='soft')

def process_images():
    import multiprocessing
    import rethinkdb as r
    c = r.connect()
    externalids = r.db('redditbooru').table('images').filter({'sourceUrl': None}).map(lambda x: x['externalId']).distinct().run(c)
    for externalid in externalids:
        process_id(externalid)
    #pool = multiprocessing.Pool(10)
    #pool.map(process_id, externalids)

if __name__ == '__main__':
    process_images()