from flask import Flask, send_from_directory, request, jsonify
import orm
from datetime import datetime, timedelta
from time import time
import conf
app = Flask(__name__)
 
session = orm.Session()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/items')
def page():
    before = datetime.fromtimestamp(int(request.args.get('before', time())))
    limit = int(request.args.get('limit', 40))
    keywords = request.args.get('keyword', '').split(',')

    query = session.query(
        orm.Image.id,
        orm.Image.thumb_url,
        orm.Image.title,
        orm.Image.date,
        orm.Image.source_name,
        orm.Image.url,
        orm.Image.atags,
    )

    if keywords[0]:
        query = query.filter(orm.Image.atags.contains(keywords))

    query = query.filter(
        orm.Image.date < before,
        orm.Image.fetched == 1,
    ).order_by(
        orm.Image.date.desc()
    ).limit(limit)

    return jsonify(
        page = [
            {
                'id': result.id,
                'thumb_url': result.thumb_url,
                'title': result.title,
                'date': int((result.date - datetime(1970, 1, 1, tzinfo=result.date.tzinfo)).total_seconds()),
                'source_name': result.source_name,
                'url': result.url,
                'tags': result.atags,
            } for result in query
        ]
    )

if __name__ == '__main__':
    app.debug = True
    app.run()