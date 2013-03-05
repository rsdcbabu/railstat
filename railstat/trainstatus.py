import cgi
import re
import time,datetime
from random import random
import simplejson as json

from google.appengine.api import users,urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MainPage(webapp.RequestHandler):
    def get(self):

        self.response.headers['Content-Type'] = 'text/html'
        txtweb_message = cgi.escape(self.request.get('txtweb-message'))
        if txtweb_message:
            if txtweb_message.__contains__(" "):
                train_number,train_start_date = txtweb_message.split()
            else:
                train_number = txtweb_message
                gmt_datetime = datetime.datetime.fromtimestamp(time.mktime(time.gmtime()))
                ist_datetime = gmt_datetime + datetime.timedelta(hours=5,minutes=30)
                ist_date = ist_datetime.date().isoformat()
                train_start_date = ist_date
            user_train_date = train_start_date
        else:
            self.response.out.write('<html><head><meta name="txtweb-appkey" content="appid" /></head><body>Get latest update on your train running status. <br /> To use, SMS @railstat &lt;train number&gt; &lt;train departure date in the format yyyy-mm-dd&gt; to 92665 92665 <br />Eg: @railstat 12631 2012-06-25</body></html>')
            return 
        random_number1 = random().__str__()[2:]
        random_number2 = random().__str__()[2:]
        current_last_station = ''
        if not current_last_station:
            train_schedule_url = 'http://stage.railyatri.in/te/schedule/%s/%s.json?callback=jQuery%s&_=%s' % (train_number, train_start_date, random_number1, random_number2)
            s = urlfetch.fetch(url=train_schedule_url,deadline=60)
            train_schedule = s.content
            json_train_schedule = json.loads(train_schedule.replace('jQuery%s('%random_number1, '').replace(')',''))
            train_station_info = {}
            all_station_codes = ''
            for each_schedule in json_train_schedule:
                if each_schedule['station_code'].strip() and each_schedule['stop']:
                    train_station_info[each_schedule['station_code']] = each_schedule
                all_station_codes = '%s,%s'%(all_station_codes,each_schedule['station_code'])
            all_station_codes = all_station_codes[1:]
            #req = 'http://coa-433841822.ap-southeast-1.elb.amazonaws.com/train/location.json?callback=jQuery%s&t=%s&s=%s&codes=%s&_=%s' % (random_number1,train_number,train_start_date,all_station_codes,random_number2)
            all_station_codes = all_station_codes.replace(',','%2C')
            req = 'http://railyatri.in/l/ajax/location.json?t=%s&s=%s&codes=%s&_=%s' % (train_number,train_start_date,all_station_codes,random_number2)
            #referer_string = 'http://railyatri.in/t/s/%s/%s?ref=start-days'%(train_number,train_start_date)
            #s = urlfetch.fetch(url=req,deadline=60,headers={'Referer':referer_string})
            main_page = urlfetch.fetch(url='http://railyatri.in',deadline=60)
            cookie_val = main_page.headers.get('Set-Cookie')
            #s = urlfetch.fetch(url=req,headers={'Cookie':'_railyatri_session=BAh7B0kiD3Nlc3Npb25faWQGOgZFRkkiJWQ1MmMwNzY0ZWNjYjU0NmJjMzg2NzhjODAzMjMwMTRkBjsAVEkiE2RhdGFfYWNjZXNzX2lkBjsARkkiFzB4MXkyeiUlOXYycyQkM2Y1ZAY7AEY%3D--c8e548e961cf3e035c07e0bfb5ccc9c293c25a33'},deadline=60)
            s = urlfetch.fetch(url=req,headers={'Cookie':cookie_val},deadline=60)
            status_content = s.content
            json_content = json.loads(status_content.replace('jQuery%s('%random_number1, '').replace(')',''))
            if json_content.has_key('keys'):
                json_key = json_content['keys']
                train_start_date = json_key[0].replace('%s_'%train_number,'')
            if not json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info'].has_key('last_stn'):
                if json_train_schedule:
                    for each_tr_stn in json_train_schedule:
                        if str(each_tr_stn['sta']) == 'None':
                            dept_time = each_tr_stn['std']
                            dept_name = each_tr_stn['station_name']
                            ft = datetime.datetime.strptime(dept_time,'%Y-%m-%dT%H:%M:%S+05:30')
                            readable_time =  '%s:%s' % (ft.hour, ft.minute)
                            readable_date =  '%s-%s-%s' % (ft.day, ft.month, ft.year)
                            self.response.out.write('<html><head><meta name="txtweb-appkey" content="appid" /></head><body>Train(%s) is scheduled to start from %s at %s (%s)<br />Thanks to Railyatri.in</body></html>'%(train_number, dept_name, readable_time, readable_date)) 
                            break
                else:
                    self.response.out.write('<html><head><meta name="txtweb-appkey" content="appid" /></head><body>Sorry, No information is available for this train. <br /> Please try again later! <br />Thanks to Railyatri.in</body></html>')
                return 
            last_location = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['station_name']
            last_location_code = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['station_code']
            last_status = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['status']
            last_time = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['time']
            current_last_station = last_location_code
           
            next_station_code = ''
            if not json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))].has_key('station_updates'):
                self.response.out.write('<html><head><meta name="txtweb-appkey" content="appid" /></head><body>Sorry, No information is available for this train. <br /> Please try again later! <br />Thanks to Railyatri.in</body></html>')
                return
            station_updates = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['station_updates']
            delay_mins = ''
            station_next_to_current = False
            for each_station_schedule in json_train_schedule:
                if each_station_schedule['station_code'] == last_location_code:
                    station_next_to_current = True
                    if last_status.startswith('arrived'):
                        last_location_sta = each_station_schedule['sta']
                    else:
                        last_location_sta = each_station_schedule['std']
                    ft = datetime.datetime.strptime(last_time,'%Y-%m-%dT%H:%M:%S+05:30')
                    ft2 = datetime.datetime.strptime(last_location_sta,'%Y-%m-%dT%H:%M:%S+05:30')
                    if ft2 > ft:
                        delay_mins = -((ft2 - ft).seconds/60)
                    else:
                        delay_mins = (ft - ft2).seconds/60
                    continue
                if not each_station_schedule['stop']:
                    continue
                if station_next_to_current:
                    if each_station_schedule['std'] == 'None':
                        next_station_code = 'ENDOFTRIP'
                    else:
                        next_station_code = each_station_schedule['station_code']
                    break
                if not last_location.strip() and last_location_code.strip():
                    if each_station_schedule['station_code'] == last_location_code:
                        last_location = each_station_schedule['station_name']
            if not last_location.strip() and last_location_code.strip():
                for each_station_schedule in json_train_schedule:
                    if each_station_schedule['station_code'] == last_location_code:
                        last_location = each_station_schedule['station_name']
                        break
            train_status = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['status']
            #if train_status != 'running':
            #    next_station_code = 'ENDOFTRIP'
            if next_station_code != 'ENDOFTRIP' and delay_mins == '':
                delay_mins = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['delay_mins']
                delay_mins = int(delay_mins)
            
            ft = datetime.datetime.strptime(last_time,'%Y-%m-%dT%H:%M:%S+05:30')
            readable_time =  '%s:%s' % (ft.hour, ft.minute)
            readable_date =  '%s-%s-%s' % (ft.day, ft.month, ft.year)
            msg = '<br /><br />Last Station: %s<br />Status: %s at %s on %s<br />Delay by: %s mins' % (last_location, last_status, readable_time, readable_date, delay_mins)
            if next_station_code and next_station_code != 'ENDOFTRIP':
                next_station_name = train_station_info[next_station_code]['station_name']
                ns_sta = train_station_info[next_station_code]['sta']
                ns_sta = datetime.datetime.strptime(ns_sta,'%Y-%m-%dT%H:%M:%S+05:30')
                ns_eta = ns_sta + datetime.timedelta(minutes=delay_mins)
                sta_time =  '%s:%s' % (ns_sta.hour, ns_sta.minute)
                sta_date =  '%s-%s-%s' % (ns_sta.day, ns_sta.month, ns_sta.year)
                eta_time =  '%s:%s' % (ns_eta.hour, ns_eta.minute)
                eta_date =  '%s-%s-%s' % (ns_eta.day, ns_eta.month, ns_eta.year)
                msg = msg+"<br /><br />Next Station update:<br /><br />Station Name: %s<br />Scheduled: %s(%s)<br />Expected: %s(%s)" % (next_station_name, sta_time, sta_date, eta_time, eta_date)
            self.response.out.write('<html><head><meta name="txtweb-appkey" content="appid" /></head><body>Train running status update - %s : %s' % (train_number, user_train_date))
            self.response.out.write(msg+"<br />Thanks to Railyatri.in</body></html>")
            

application = webapp.WSGIApplication(
                                     [('/trainstatus', MainPage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
