from flask import Flask, send_from_directory, request, jsonify
import rethinkdb as r
from datetime import datetime
from time import time
import conf
app = Flask(__name__)
 

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/awwni')
def page():
    before = r.epoch_time(int(request.args.get('before', time())))
    limit = int(request.args.get('limit', 40))
    return jsonify(
        page = list(
            db
            .table('images')
            .order_by(index=r.desc('dateCreated'))
            .filter(r.row['dateCreated'] < before)
            .limit(limit)
            .map(lambda row: row.merge({
                'timestamp': row['dateCreated'].to_epoch_time(),
                'thumburl': r.add(conf.thumbprefix, '/', row['basename'], '.500.webp'),
                'fullurl': r.add(conf.fullprefix, '/', row['basename'], '.', row['type']),
                'redditurl': r.add("https://reddit.com/r/", row['sourceName'], '/comments/', row['externalId']),
            }))
            .run(c))
    )

db = r.db('redditbooru')
c = r.connect()

if __name__ == '__main__':
    app.debug = True
    app.run()