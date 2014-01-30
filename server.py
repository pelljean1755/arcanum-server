from flask import Flask,make_response,jsonify,request,send_file
from flask.ext.restful import Api,Resource,reqparse
import werkzeug
from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy
from ofs.local import PTOFS
import base64
app=Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
o=PTOFS()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password =db.Column(db.String(120), unique=False)
    key = db.Column(db.String(200),unique=True)
    uuid = db.Column(db.String(200),unique=True)

    def __init__(self, username, email, passw, key,uuid):
        self.username = username
        self.email = email
        self.password = passw
        self.key = key
        self.uuid = uuid

    def __repr__(self):
        return '<User %r>' % self.username
@auth.get_password
def get_pw(username):
    user=User.query.filter_by(username=username).first()
    if user:
        return user.password
    return None
@auth.error_handler
def unauthorized():
    return make_response(jsonify( { 'message': 'Unauthorized access' } ), 401)


class SendAPI(Resource):
	decorators = [auth.login_required]
	def __init__(self):
		self.reqparse=reqparse.RequestParser()
		self.reqparse.add_argument('file', type=werkzeug.datastructures.FileStorage, location='files')
		super(SendAPI, self).__init__()
	def get(self,id):
		user=User.query.filter_by(username=id).first()
		if user and id != "all":
		    return {"Id":id,"key":user.key}
		if id == "all":
			k=[]
			lst=User.query.all()
			for i in lst:
				k.append(i.username)
			return k
	def post(self,id):
		details=id.split("/")
		user=User.query.filter_by(username=details[0]).first()
		uuid=user.uuid
		o.put_stream(uuid,details[1],self.reqparse.parse_args()["file"].stream.read())
		return 200
class ReceiveAPI(Resource):
	decorators = [auth.login_required]

	def get(self,id):
		user=User.query.filter_by(username=auth.username()).first()
		if user:
			files=o.list_labels(user.uuid)
			print id
			if id=="all":
				return files 
			elif int(id) < len(files)+1:
				label=o.list_labels(user.uuid)[int(id)-1]
				return send_file(o.get_url(user.uuid,label)[7:])
				# base=base64.encodestring(data)
				# print len(base),len(data)
				# return base
			else:
				return "Invalid id"
	def post(self,id):
		pass
class Authenticate(Resource):
	decorators = [auth.login_required]

	def get(self):
		return 200
class CreateUser(Resource):
	def get(self,detail):
		det=detail.split(":")
		if len(det)==7:
			usern=det[0]
			passw=det[1]
			email=det[2]
			# lst = [random.choice(string.ascii_letters + string.digits) for n in xrange(30)]
			# key = "".join(lst)
			key=":".join(det[3:])
			uuid=o.claim_bucket()
			user=User(usern,email,passw,key,uuid)
			db.session.add(user)
			db.session.commit()
			return {"Details":detail,"key":key}
		else:
			return {"Error":"Not enough values"}

api.add_resource(SendAPI,'/send/<path:id>')
api.add_resource(ReceiveAPI,'/receive/<path:id>')
api.add_resource(CreateUser,'/create/<path:detail>')
api.add_resource(Authenticate,'/auth/')

if __name__ == '__main__':
    app.run(debug = True)