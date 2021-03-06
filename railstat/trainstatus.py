import cgi
import re
import time,datetime
import simplejson as json
import urllib

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
            self.response.out.write('<html><head><meta name="txtweb-appkey" content="app-id" /></head><body>Get latest update on your train running status. <br /> To use, SMS @railstat &lt;train number&gt; &lt;train departure date in the format yyyy-mm-dd&gt; to 92665 92665 <br />Eg: @railstat 12631 2012-06-25</body></html>')
            return 
        main_page = urlfetch.fetch(url='http://trainenquiry.com',deadline=60)
        cookie_val = main_page.headers.get('Set-Cookie')
        train_schedule = self._get_train_schedule(train_start_date,train_number,cookie_val)
        json_train_schedule = json.loads(train_schedule)
        train_station_info = {}
        all_station_codes = ''
        for each_schedule in json_train_schedule:
            if each_schedule['station_code'].strip() and each_schedule['stop']:
                train_station_info[each_schedule['station_code']] = each_schedule
            all_station_codes = '%s,%s'%(all_station_codes,each_schedule['station_code'])
        all_station_codes = all_station_codes[1:]
        status_content = self._get_train_location_info(train_start_date,train_number,all_station_codes,cookie_val)
        json_content = json.loads(status_content)
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
                        self.response.out.write('<html><head><meta name="txtweb-appkey" content="app-id" /></head><body>Train(%s) is scheduled to start from %s at %s (%s)<br />Thanks to Railyatri.in</body></html>'%(train_number, dept_name, readable_time, readable_date)) 
                        break
            else:
                self.response.out.write('<html><head><meta name="txtweb-appkey" content="app-id" /></head><body>Sorry, No information is available for this train. <br /> Please try again later! <br />Thanks to Railyatri.in</body></html>')
            return 
        last_location = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['station_name']
        last_location_code = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['station_code']
        last_status = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['status']
        last_time = json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))]['running_info']['last_stn']['time']
        current_last_station = last_location_code
       
        next_station_code = ''
        if not json_content['%s_%s'%(train_number,train_start_date.replace('-','_'))].has_key('station_updates'):
            self.response.out.write('<html><head><meta name="txtweb-appkey" content="app-id" /></head><body>Sorry, No information is available for this train. <br /> Please try again later! <br />Thanks to Railyatri.in</body></html>')
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
        self.response.out.write('<html><head><meta name="txtweb-appkey" content="app-id" /></head><body>Train running status update - %s : %s' % (train_number, user_train_date))
        self.response.out.write(msg+"<br />Thanks to Railyatri.in</body></html>")
            
    def _get_train_schedule(self,train_start_date,train_number,cookie_val):
        train_schedule_url = 'http://www.trainenquiry.com/RailYatri.ashx'
        payload_data = {}
        payload_data['RequestType'] = 'Schedule'
        payload_data['date_variable'] = train_start_date
        payload_data['train_number_variable']  = train_number
        payload_data = urllib.urlencode(payload_data)
        req_headers = {}
        req_headers['Cookie'] = cookie_val
        req_headers['Referer'] = 'http://trainenquiry.com/CurrentRunningTrain.aspx'
        s = urlfetch.fetch(url=train_schedule_url,payload=payload_data,method=urlfetch.POST,headers=req_headers,deadline=60)
        train_schedule = s.content
        return train_schedule

    def _get_train_location_info(self,train_start_date,train_number,all_station_codes,cookie_val):
        train_schedule_url = 'http://www.trainenquiry.com/RailYatri.ashx'
        payload_data = {}
        payload_data['RequestType'] = 'Location'
        payload_data['codes'] = all_station_codes
        payload_data['s'] = train_start_date
        payload_data['t']  = train_number
        payload_data = urllib.urlencode(payload_data)
        req_headers = {}
        req_headers['Cookie'] = cookie_val
        req_headers['Referer'] = 'http://trainenquiry.com/CurrentRunningTrain.aspx'
        s = urlfetch.fetch(url=train_schedule_url,payload=payload_data,method=urlfetch.POST,headers=req_headers,deadline=60)
        status_content = s.content
        return status_content

application = webapp.WSGIApplication(
                                     [('/trainstatus', MainPage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
