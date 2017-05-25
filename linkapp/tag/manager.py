import redis
from .queue import TagMessenger
from .wrapper import ServiceWrapper, NotFound

import strict_rfc3339
from datetime import datetime

class TagManager:
    
    def __init__(self, redis_url="redis://localhost:6379/0", 
                       rabbit_url="amqp://localhost"):
    
        self.connection = redis.StrictRedis.from_url(redis_url, decode_responses=True)
        self.tag_messenger = TagMessenger(rabbit_url)
        
    def tag_key(self, tag):
        return "tag:{}".format(tag)
    
    def link_key(self, link_id):
        return "link-tags:{}".format(link_id)
    
    def replace_tags(self, link_id, *tags):
        if not tags:
            raise ValueError("At least one tag must be specified")
            
        existing_tags = self.list_tags(link_id)
            
        with self.connection.pipeline() as pipe:
            for tag in existing_tags:
                self._tag_unlink(pipe, tag, link_id)
            
            for tag in tags:
                self._tag_link(pipe, tag, link_id)
                
            results = pipe.execute()
            
        self.tag_messenger.retagged(link_id, existing_tags, tags)
           
    
    def add_tags(self, link_id, *tags):
        if not tags:
            raise ValueError("At least one tag must be specified")
            
        with self.connection.pipeline() as pipe:
            for tag in tags:
                self._tag_link(pipe, tag, link_id)
                
            results = pipe.execute()
            
        self.tag_messenger.tagged(link_id, *tags)
    
    def remove_tags(self, link_id, *tags):
        if not tags:
            raise ValueError("At least one tag must be specified")
            
        with self.connection.pipeline() as pipe:
            for tag in tags:
                self._tag_unlink(pipe, tag, link_id)
            
            results = pipe.execute()
            
        self.tag_messenger.untagged(link_id, *tags)
    
    def _tag_unlink(self, pipe, tag, link_id):
        pipe.srem(self.link_key(link_id), tag)
        pipe.zrem(self.tag_key(tag), link_id)
    
    def _tag_link(self, pipe, tag, link_id):
        score = strict_rfc3339.rfc3339_to_timestamp(strict_rfc3339.now_to_rfc3339_utcoffset())
        
        pipe.zadd(self.tag_key(tag), score, link_id)
        
        pipe.sadd(self.link_key(link_id), tag)
    
    
    def add_links(self, tag, *link_ids):
        if not link_ids:
            raise ValueError("At least one link_id must be specified")
        
        with self.connection.pipeline() as pipe:
            for link_id in link_ids:
                self._tag_link(pipe, tag, link_id)
                
            results = pipe.execute()
            
        for link_id in link_ids:
            self.tag_messenger.tagged(link_id, tag)
    
    def remove_links(self, tag, *link_ids):
        if not link_ids:
            raise ValueError("At least one link_id must be specified")
        
        key = self.tag_key(tag)
        
        with self.connection.pipeline() as pipe:
            for link_id in link_ids:
                pipe.zrem(key, link_id)
                
            results = pipe.execute()
            
        for link_id in link_ids:
            self.tag_messenger.untagged(link_id, tag)
    
    def list_tags(self, link_id):
        
        key = self.link_key(link_id)
        
        result = self.connection.smembers(key)
        self.tag_messenger.viewed_link_tags(link_id)
        
        return result
    
    def count_links(self, tag):
        key = self.tag_key(tag)
        
        result = self.connection.zcard(key)
        
        return result
    
    def list_links(self, tag, start=0, stop=-1):
        key = self.tag_key(tag)
        
        result = self.connection.zrevrange(key, start, stop)
        
        self.tag_messenger.viewed_tag(tag)
        
        return result