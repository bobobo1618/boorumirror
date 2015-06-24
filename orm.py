import conf
from datetime import datetime
from dateutil.parser import parse as dateparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, mapper

engine = create_engine('postgresql://localhost/awwnime', client_encoding='utf8')

Session = sessionmaker(bind=engine)
Base = declarative_base()

from sqlalchemy import Column
from sqlalchemy.schema import ForeignKey, Table
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Integer, Unicode, DateTime, BigInteger, Boolean, UnicodeText

class Tag(Base):
    __tablename__ = 'tags'
    name = Column(Unicode(length=128), unique=True, primary_key=True)
    type = Column(Unicode(length=256))

class Image(Base):
    __tablename__ = 'images'
    id = Column(BigInteger, primary_key=True)
    title = Column(Unicode(length=512))
    text = Column(UnicodeText)
    url = Column(Unicode(length=1024))
    date = Column(DateTime)
    height = Column(Integer)
    width = Column(Integer)
    remote_id = Column(BigInteger)
    nsfw = Column(Boolean)

    source_url = Column(Unicode(length=1024))
    full_url = Column(Unicode(length=1024))
    thumb_url = Column(Unicode(length=1024))
    remote_url = Column(Unicode(length=1024))

    set_id = Column(Unicode(length=10))

    size = Column(Integer)
    name = Column(Unicode(length=128))
    extension = Column(Unicode(length=6))
    fetched = Column(Integer)

    atags = Column(ARRAY(UnicodeText))
    source_name = Column(Unicode(length=64), ForeignKey('sources.shortname'))
    source = relationship("Source", backref='images')

    @classmethod
    def from_awwnime_response(cls, response):
        basename = response['cdnUrl'].split('/')[-1].split('.')[0]
        db_dict = {
            'title': unicode(response['title']),
            'text': unicode(response['caption']) if response['caption'] else None,
            'url': 'https://reddit.com/tb/' + response['externalId'].decode('utf-8'),
            'date': datetime.fromtimestamp(response['dateCreated']),
            'height': response['height'],
            'width': response['width'],
            'remote_id': response['imageId'],
            'nsfw': response['nsfw'],
            'set_id': response['externalId'],
            'source_url': unicode(response['sourceUrl']) if response['sourceUrl'] else u'',
            'full_url': unicode(conf.fullprefix + '/%s.%s' % (basename, response['type'])),
            'thumb_url': unicode(conf.thumbprefix + '/%s.500.webp' % basename),
            'remote_url': unicode('https://s3.amazonaws.com/cdn.awwni.me/%s.%s' % (basename, response['type'])),
            'name': unicode(basename),
            'extension': unicode(response['type']),
            'fetched': 0,
            'source_name': u'awwnime',
        }
        image_obj = cls(**db_dict)
        tags = response['keywords'].split(' ') + ['r/' + response['sourceName']]
        image_obj.atags = list({unicode(tag) for tag in tags})
        new_tags = [
            Tag(name=unicode(keyword))
            for keyword in tags
        ]
        return image_obj, new_tags

    @classmethod
    def from_danbooru_response(cls, response, fork=False, fork_url_format=u'https://konachan.com/post/show/%d/', fork_name=u'konachan'):
        db_dict = {
            'remote_id': int(response['id']),
            'source_url': response['source'],
            'size': int(response['file_size']) if response['file_size'] else None,
            'fetched': 0,
        }

        tags = []

        if not fork:
            db_dict.update({
                'date': dateparse(response['created_at']),
                'url': u'https://danbooru.donmai.us/posts/%d' % response['id'],
                'height': int(response['image_height']),
                'width': int(response['image_width']),
                'nsfw': response['is_banned'] == True,
                'remote_url': 'https://danbooru.donmai.us' + response['file_url'],
                'extension': response['file_ext'],
                'source_name': u'danbooru',
                'name': response['file_url'].split('/')[-1].split('.')[0],
            })

            tags += [
                (keyword, None)
                for keyword in
                response['tag_string_general'].split(' ')
            ]
            for tagname in (u'artist', u'character', u'copyright'):
                if int(response['tag_count_' + tagname]) >= 1:
                    strings = set(response['tag_string_' + tagname].split(' '))
                    if u'loli' in strings:
                        return
                    tags += [
                        (string, tagname)
                        for string in strings
                    ]
        else:
            db_dict.update({
                'date': datetime.fromtimestamp(response['created_at']),
                'url': fork_url_format % response['id'],
                'height': int(response['height']),
                'width': int(response['width']),
                'remote_url': response['file_url'],
                'extension': response['file_url'].split('/')[-1].split('.')[-1],
                'source_name': fork_name,
                'name': response['md5'],
            })
            keywords = set(response['tags'].split(' '))
            if u'loli' in keywords:
                return
            tags += [
                (keyword, None)
                for keyword in keywords
            ]

        db_dict.update({
            'full_url': unicode(conf.fullprefix + '/%s.%s' % (db_dict['name'], db_dict['extension'])),
            'thumb_url': unicode(conf.thumbprefix + '/%s.500.webp' % db_dict['name']),
        })

        image_obj = cls(**db_dict)
        tags = set(tags)
        new_tags = []

        for tag in tags:
            new_tag = Tag(name=tag[0])
            if tag[1]:
                new_tag.type = tag[1]
            new_tags.append(new_tag)

        image_obj.atags = list({tag[0] for tag in tags})
        return image_obj, new_tags


class Hash(Base):
    __tablename__ = 'hashes'
    id = Column(BigInteger, primary_key=True)
    name = Column(Unicode(length=256))
    value = Column(BigInteger)
    image_id = Column(BigInteger, ForeignKey('images.id'))
    image = relationship("Image", backref='hashes')

class Source(Base):
    __tablename__ = 'sources'
    name = Column(Unicode(length=256))
    shortname = Column(Unicode(length=64), unique=True, primary_key=True)

