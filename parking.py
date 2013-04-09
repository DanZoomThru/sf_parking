import webapp2
import jinja2
import os
import urllib2
import urlparse
import cgi, cgitb
from os import curdir, sep
import difflib
import sys
import xml.etree.cElementTree as ET
from  xml.dom import minidom
from google.appengine.api import urlfetch
import time
from collections import defaultdict
import json
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class MainPage(webapp2.RequestHandler):
  def get(self):
        routelist=defaultdict(dict)
        routes=urlfetch.fetch(url="http://webservices.nextbus.com/service/publicXMLFeed?command=routeList&a=sf-muni").content
        tree=ET.fromstring(routes)
        for info in tree:
            tag=info.get('tag')
            title=info.get('title')
            routelist[tag]=title
        template_values={
        'routes': routelist,
        }
        template = jinja_environment.get_template('home.html')
        self.response.out.write(template.render(template_values))

class Parking(webapp2.RequestHandler):
    """Receives lat and long from html and calls API"""
    def post(self):
        location=list()
        lat=list()
        lng=list()
        name=list()
        desc=list()
        phone=list()
        occ=list()
        avail=list()
        typeof=list()
        latitude=self.request.POST["latitude"]
        longitude=self.request.POST["longitude"]
        #latitude=str(37.792275)
        #longitude=str(-122.397089)
        data=urllib2.urlopen("http://api.sfpark.org/sfpark/rest/availabilityservice?lat="+latitude +"&long="+longitude+"&radius=0.75&uom=mile&response=xml")
        tree=ET.parse(data)
        root=tree.getroot()
        for child in root:
            for subchild in child:
                if 'LOC' in subchild.tag:
                    coords=subchild.text.split(",")
                    lng.append(coords[0])
                    lat.append(coords[1])
                    #location.append(type(subchild.text))
                if 'TYPE' in subchild.tag:
                    typeof.append(subchild.text)    
                if 'NAME' in subchild.tag:
                    name.append(subchild.text)
                if 'DESC' in subchild.tag:
                    desc.append(subchild.text)
                if 'TEL' in subchild.tag:
                    phone.append(subchild.text)
                if 'OCC' in subchild.tag:
                    occ.append(int(subchild.text))
                if 'OPER' in subchild.tag:
                    avail.append(int(subchild.text))
        template_values={
        'latitude': lat, 
        'longitude': lng,
        'name': name,
        'description': desc,
        'phone': phone,
        'taken': occ,
        'total': avail,
        'js_code': 'alert("test: pancake")', 
        }
        #template = jinja_environment.get_template('park.html')
        self.response.out.write(json.dumps({'latitude': lat, 'longitude': lng, 'name1': name, 'desc': desc, 'phone': phone, 'taken': occ, 'total': avail, 'kind': typeof}))
        #self.response.out.write(template.render(template_values))
class FindStops(webapp2.RequestHandler):
    """Receives line from html page, finds all of the stops for it"""
    def post(self):
        
        stopnames=defaultdict(dict)
        tagnumbers=defaultdict(dict)
        stopnames1=defaultdict(dict)
        

        bound=self.request.POST["bound"]
        line=self.request.POST["stop"]
        stops=urlfetch.fetch(url="http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=sf-muni&r=" + line).content
        
        tree=ET.fromstring(stops)
        title=list()
        #Finds all stops
        for info in tree[0].findall('stop'):
            stopname=info.get('title')
            tag=info.get('tag')
            stopnames[tag]=stopname
            tagnumbers[stopname]=tag
        #Narrows it down, finds all the stops for the indicated direction    
        for info in tree[0].findall('direction'):
            if info.get('name') == bound:
                for subinfo in info:
                    title.append(subinfo.get('tag'))
        #Matches stops with direction
        for name in title:
            stopnames1[name]=stopnames[name]
        template_values = {
            'stopnames': stopnames1,
            'title': title,
            'route':line,

        }
        template = jinja_environment.get_template('stops.html')
        self.response.out.write(template.render(template_values))


class Times(webapp2.RequestHandler):
    def post(self):
        """Receives stop from html page, sends times to template"""
        minutes=list()
        stop=self.request.POST["stop"]
        line=self.request.POST["line"]
        lat=defaultdict(dict)
        lng=defaultdict(dict)
        
        #fetches lat/lng for each stop id number for the selected line
        stops=urlfetch.fetch(url="http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=sf-muni&r=" + line).content
        tree=ET.fromstring(stops)
        
        #Parses lat/lng into dictionaries
        for info in tree[0].findall('stop'):
            tag=info.get('tag')
            lat[tag]=(float(info.get('lat')))
            lng[tag]=(float(info.get('lon')))
        latitude=lat[stop]#Finds exact lat and lng for the specific stop
        longitude=lng[stop]
        self.response.out.write(json.dumps({'latitude': lat[stop], 'longitude': lng[stop]}))
        

class Final(webapp2.RequestHandler):
    def post(self):
        """Receives stop and time in order to print out minutes"""
        minutes=list()
        stop=self.request.POST["stop"]
        line=self.request.POST["line"]
        time=urlfetch.fetch("http://webservices.nextbus.com/service/publicXMLFeed?command=predictions&a=sf-muni&s="+stop+"&r="+line).content
        tree=ET.fromstring(time)
        #Not sure if triply nested loop is clean
        for child in tree:
            for info in child:
                for times in info:
                    minutes.append(times.get('minutes'))
        if(len(minutes)==0):
            flag=1
        else:
            flag=0
        template_values={
            'minutes': minutes,
            'flag': flag,
        }

        template=jinja_environment.get_template('times.html')
        self.response.out.write(template.render(template_values))




app = webapp2.WSGIApplication([('/', MainPage), ('/stops', FindStops), ('/times', Times), ('/final', Final), ('/parking', Parking)], debug=True)
