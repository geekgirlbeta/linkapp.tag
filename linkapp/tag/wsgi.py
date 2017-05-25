from webob import Response, Request

from .manager import TagManager
from .queue import TagMessenger

from urllib import parse

import math

import jsonschema

pagination_schema = {
    "type": "object",
    "properties": {
        "page": { "type": "integer" }
    }
}

add_links_schema = {
    "type": "object",
    "properties": {
        "links": { "type": "array",
                   "items": {
                       "type": "string"
                   },
                   "minItems": 1
        }
    },
    "required": ["links"]
}

add_tags_schema = {
    "type": "object",
    "properties": {
        "tags": { "type": "array",
                   "items": {
                       "type": "string"
                   },
                   "minItems": 1
        }
    },
    "required": ["tags"]
}


def bad_request(environ, start_response, msg="Bad Request", status=400):
    res = Response(msg, status=status)
    
    return res(environ, start_response)

class BadRequest(Exception):
    """
    Raised when something bad happened in a request
    """
    
class NotFound(Exception):
    """
    Raised when something is not found.
    """
    
class UnsupportedMediaType(Exception):
    """
    Raised when a bad content type is specified by the client.
    """

class TagMicroservice:
    
    def __init__(self, config):
        self.config = config
        self.tag_manager = TagManager(self.config.redis_url, self.config.rabbit_url)
            
        self.link_messenger = TagMessenger(self.config.rabbit_url)
    
    def __call__(self, environ, start_response):
        req = Request(environ, charset="utf8")
        
        new_path = parse.unquote(req.path)
        
        parts = new_path.split("/")[1:]
        
        print(parts)
        
        try:
            if req.content_type != "application/json":
                raise UnsupportedMediaType()
            
            if parts[0] == "tag":
                if len(parts) != 2:
                    raise BadRequest()
                else:
                    tag = parts[1]
                    
                    if req.method == 'GET':
                        result = self.list_links(req, tag)
                    elif req.method == 'POST':
                        result = self.add_links(req, tag)
                    elif req.method == 'DELETE':
                        result = self.remove_links(req, tag)
                    else:
                        raise BadRequest()
            elif parts[0] == "link":
                if len(parts) != 2:
                    raise BadRequest()
                else:
                    link_id = parts[1]
                    
                    if req.method == 'GET':
                        result = self.list_tags(req, link_id)
                    elif req.method == 'POST':
                        result = self.add_tags(req, link_id)
                    elif req.method == 'PUT':
                        result = self.replace_tags(req, link_id)
                    elif req.method == 'DELETE':
                        result = self.remove_tags(req, link_id)
                    else:
                        raise BadRequest()
            else:
                raise BadRequest()
        except BadRequest as e:
            return bad_request(environ, start_response)
        except ValueError as e:
            return bad_request(environ, start_response, str(e))
        except UnsupportedMediaType:
            return bad_request(environ, start_response, "Unsupported media type", 415)
        except NotFound:
            return bad_request(environ, start_response, "Not Found", 404)
        except jsonschema.ValidationError as e:
           return bad_request(environ, start_response, e.message)
            
        res = Response()
        res.json = result
        return res(environ, start_response)
    
    def add_links(self, req, tag):
        data = req.json
        
        jsonschema.validate(data, add_links_schema)
        
        links = data['links']
        
        return self.tag_manager.add_links(tag, *links)
    
    def remove_links(self, req, tag):
        data = req.json
        
        jsonschema.validate(data, add_links_schema)
        
        links = data['links']
        
        return self.tag_manager.remove_links(tag, *links)

    def list_links(self, req, tag):
        data = req.GET.mixed()
        
        try:
            data['page'] = int(data.get('page', 1))
        except ValueError:
            raise BadRequest("Invalid page number")
        
        jsonschema.validate(data, pagination_schema)
        
        page = data.get("page", 1)
        
        per_page = self.config.listing_per_page
        count = self.tag_manager.count_links(tag)
        last = int(math.ceil(count/per_page))
        
        if page > last:
            page = last
        
        if page < 1:
            page = 1
        
        stop = page*per_page-1
        start = page*per_page-per_page
        
        next = page+1
        previous = page-1
        
        links = self.tag_manager.list_links(tag, start=start, stop=stop)
        
        if next > last:
            next = None
            
        if previous < 1:
            previous = None
        
        return {
            'links': links,
            'pagination': {
                'next': next,
                'previous': previous,
                'count': count,
                'last': last
            }
        }
    
    def add_tags(self, req, link_id):
        data = req.json
        
        jsonschema.validate(data, add_tags_schema)
        
        return self.tag_manager.add_tags(link_id, *data['tags'])
    
    def list_tags(self, req, link_id):
        return list(self.tag_manager.list_tags(link_id))
    
    def remove_tags(self, req, link_id):
        data = req.json
        
        jsonschema.validate(data, add_tags_schema)
        
        return self.tag_manager.remove_tags(link_id, *data['tags'])
    
    def replace_tags(self, req, link_id):
        data = req.json
        
        jsonschema.validate(data, add_tags_schema)
        
        return self.tag_manager.replace_tags(link_id, *data['tags'])
 
    