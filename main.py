#coding:utf-8
# Last modified: 2018-08-07 23:11:05
# by zhangdi http://jondy.net/
import os.path
import time
import json
import psutil
import httplib
import datetime
import peewee
import tornado.ioloop
import tornado.web
import tornado.template as template
from playhouse.shortcuts import model_to_dict, dict_to_model

#format_time = lambda x: datetime.datetime.utcfromtimestamp(x).strftime('%Y-%m-%dT%H:%M:%SZ')
format_time = lambda x: datetime.datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S')

ERRORPAGE = '''<!DOCTYPE html>
<html style="height:100%">
<head><meta charset="UTF-8"><title> {{ code }} {{ msg }}</title>
<style>.btn{display:block;width: 145px;height: 45px;font-size: 14px;margin:0 auto;line-height: 45px;
background-color:#234;color: #fff;text-align: center;text-decoration: none;}</style>
</head>
<body style="color: #444; margin:0;font: normal 14px/20px Arial, Helvetica, sans-serif; height:100%; background-color: #fff;">
<div style="height:auto; min-height:100%; ">     <div style="text-align: center; width:800px; margin-left: -400px; position:absolute; top: 30%; left:50%;">
<h1 style="margin:0; font-size:150px; line-height:150px; font-weight:bold;">{{ code }}</h1>
<h2 style="margin-top:20px;font-size: 30px;">{{ msg }}
</h2>
<p style="margin-top:60px;"><a href="/" class="btn">返回首页</a></p>
</div></div></body></html>
'''

db = peewee.SqliteDatabase(os.path.join(os.path.dirname(__file__), "db", "test.db"))

class BaseModel(peewee.Model):
    class Meta:
        database = db

class User(BaseModel):
    id = peewee.PrimaryKeyField()
    username = peewee.CharField(null = False)
    password = peewee.CharField(null = False)
    class Meta:
        db_table = 'user'

class Channel(BaseModel):
    id = peewee.PrimaryKeyField()
    name = peewee.CharField(null = False)
    rtp = peewee.CharField(null = False)
    m3u8 = peewee.CharField(null = False)
    class Meta:
        db_table = 'channel'

# init db
User.create_table()
_, created = User.get_or_create(id=1, username='admin', defaults={'password': 'admin'})
Channel.create_table()
_, created = Channel.get_or_create(id=1, defaults={'name': 'cctv1', 'rtp': '10.10.10.11:5004', 'm3u8': '/hls/cctv1.m3u8'})
_, created = Channel.get_or_create(id=2, defaults={'name': 'cctv2', 'rtp': '10.10.10.12:5004', 'm3u8': '/hls/cctv2.m3u8'})
_, created = Channel.get_or_create(id=3, defaults={'name': 'cctv3', 'rtp': '10.10.10.13:5004', 'm3u8': '/hls/cctv3.m3u8'})

class BaseHandler(tornado.web.RequestHandler):
    '''基本http类'''
    def get_current_user(self):
        return self.get_secure_cookie("user")

    def write_error(self, status_code, **kwargs):
        msg = httplib.responses[status_code]
        self.finish(template.Template(ERRORPAGE).generate(code=status_code, msg=msg))

    def data_received(self, data):
        return data

    def get(self, *args, **kwargs):
        self.set_status(404)
        self.finish(template.Template(ERRORPAGE).generate(code='404', msg='Not Found'))

class LoginHandler(BaseHandler):
    '''用户登录类'''
    def get(self):
        user = self.get_current_user()
        redirect_to = '/' # self.get_argument('next', '/')
        #if user: self.redirect('/')
        self.render('login.html', title=u'用户登录', path=None, next=redirect_to)

    def post(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        redirect_to = self.get_argument('next', '/')
        username = self.get_argument('username', '')
        password = self.get_argument('password', '')
        obj = User.select().where((User.username == username) & (User.password == password))
        if obj:
            self.set_secure_cookie("user", username)
            resp = {'code': 1}
            resp['redirect_to'] = redirect_to
        else:
            print 2
            resp = {'code': 0, 'msg': '用户名密码错误'}
        self.finish(resp)

class LogoutHandler(BaseHandler):
    '''用户注销类'''
    @tornado.web.authenticated
    def get(self):
        user = self.get_current_user()
        if user:
            self.clear_all_cookies()
            self.redirect("/logout/")
        else:
            self.render('logout.html', title=u'用户退出', path=None)

class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("index.html")

class ChannelHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        objs = Channel.select().order_by(Channel.id)
        self.render("channel.html", objs=objs, format_time=format_time)

    @tornado.web.authenticated
    def post(self):
        pk = self.get_argument('id')
        name = self.get_argument('name')
        rtp = self.get_argument('rtp')
        m3u8 = self.get_argument('m3u8')
        if pk: # update
            obj = Channel.select().where(Channel.id==pk).get()
            obj.name = name
            obj.rtp = rtp
            obj.m3u8 = m3u8
            obj.save()
        else: # create
            Channel.create(name=name, rtp=rtp, m3u8=m3u8)
        self.finish({'code': 1})

    @tornado.web.authenticated
    def delete(self):
        pk = self.get_argument('pk')
        Channel.get(Channel.id==pk).delete_instance()
        resp = {'code': 1}
        self.finish(resp)

    def _api_data(self):
        objs = Channel.select().order_by(Channel.id)
        data = []
        for obj in objs:
            data.append(model_to_dict(obj))
        return json.dumps(data)

class ProcessHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        objs = psutil.process_iter()
        self.render("process.html", objs=objs, format_time=format_time)

def schedule_func():
    #DO SOMETHING#
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name'])
        except psutil.NoSuchProcess:
            pass
        else:
            pass
            #print pinfo

if __name__ == "__main__":

    application = tornado.web.Application([
            (r"/", MainHandler),
            (r"/login/", LoginHandler),
            (r"/logout/", LogoutHandler),
            (r"/channel/", ChannelHandler),
            (r"/process/", ProcessHandler),
        ],
        default_handler_class=BaseHandler,
        cookie_secret="mysecret",
        login_url="/login/",
        #default_handler_class=BaseHandler,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=False,
        debug=True,
    )
    application.listen(8000)

    interval_ms = 1000
    main_loop = tornado.ioloop.IOLoop.instance()
    sched = tornado.ioloop.PeriodicCallback(schedule_func,interval_ms)
    sched.start()
    main_loop.start()
