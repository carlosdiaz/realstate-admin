import os
import os.path as op
from flask import Flask, url_for, redirect, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask_security.utils import encrypt_password
import flask_admin
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers

from sqlalchemy.event import listens_for
from jinja2 import Markup
from datetime import datetime
from flask_admin import Admin, form

# Create Flask application
#app = Flask(__name__)
app = Flask(__name__, static_folder='/home/carlos/FlaskProject/RealState/static')
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)

# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), '/home/carlos/FlaskProject/RealState/static')
#try:
#    os.mkdir(file_path)
#except OSError:
#    pass



# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return self.email


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)



class Property(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.String(80))
    typeprop = db.Column(db.String(80))
    contract = db.Column(db.String(80))
    location = db.Column(db.String(80))
    state = db.Column(db.String(80))
    city = db.Column(db.String(80))
    bathrooms = db.Column(db.String(10))
    bedrooms = db.Column(db.String(10))
    area = db.Column(db.String(20))
    features = db.Column(db.String(80))
    description = db.Column(db.String(250))
    pub_date = db.Column(db.DateTime)


    def __init__(self, price, typeprop, contract, location, state, city, bathrooms, bedrooms, area, features, description, pub_date=None):
        self.price = price
        self.typeprop = typeprop
        self.contract = contract
        self.location = location
        self.state = state
        self.city = city
        self.bathrooms = bathrooms
        self.bedrooms = bedrooms
        self.area = area
        self.features = features
        self.description = description

        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date

    def __init__(self, price = '', typeprop = '',  contract='', location='', state='', city='', bathrooms='', bedrooms='', area='', features='', description='', pub_date=None):        
        self.price = price
        self.typeprop = typeprop
        self.contract = contract
        self.location = location
        self.state = state
        self.city = city
        self.bathrooms = bathrooms
        self.bedrooms = bedrooms
        self.area = area
        self.features = features
        self.description = description

        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date


    def __repr__(self):
        return 'Id %r' % self.id


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(64))
    path = db.Column(db.Unicode(128))

    property_id = db.Column(db.Integer, db.ForeignKey('property.id'))
    property = db.relationship('Property',
        backref=db.backref('property', lazy='dynamic'))

    def __init__(self, name, property_id):
        self.name = name
        self.property_id = property_id

    #Following constructor is required for creating new Images
    def __init__(self, name = '', property_id = ''):
        self.name = name
        self.property_id = property_id




# Delete hooks for models, delete files if models are getting deleted
@listens_for(Image, 'after_delete')
def del_image(mapper, connection, target):
    if target.path:
        # Delete image
        try:
            os.remove(op.join(file_path, target.path))
        except OSError:
            pass

        # Delete thumbnail
        try:
            os.remove(op.join(file_path,
                              form.thumbgen_filename(target.path)))
        except OSError:
            pass



class PropertyView(sqla.ModelView):
    column_display_pk = True
    form_columns = ['id', 'price', 'typeprop', 'contract' , 'location' , 'state' , 'city' , 'bathrooms' , 'bedrooms', 'area', 'features', 'description']


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('superuser'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class ImageView(MyModelView):
    def _list_thumbnail(view, context, model, name):
        if not model.path:
            return ''

        return Markup('<img src="%s">' % url_for('static',
                                                 filename=form.thumbgen_filename(model.path)))

    column_formatters = {
        'path': _list_thumbnail
    }

    # Alternative way to contribute field is to override it completely.
    # In this case, Flask-Admin won't attempt to merge various parameters for the field.
    form_extra_fields = {
        'path': form.ImageUploadField('Image',
                                      base_path=file_path,
                                      thumbnail_size=(100, 100, True))
    }


# Flask views
@app.route('/')
def index():
    return render_template('index.html')

# Create admin
admin = flask_admin.Admin(
    app,
    'Admin real state',
    base_template='my_master.html',
    template_mode='bootstrap3',
)

# Add model views
admin.add_view(MyModelView(Role, db.session))
admin.add_view(MyModelView(User, db.session))

admin.add_view(MyModelView(Property, db.session))

#admin.add_view(MyModelView(Image, db.session))
admin.add_view(ImageView(Image, db.session))

# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
    )




if __name__ == '__main__':

    # Create DB
    db.create_all()

    '''with app.app_context():
        user_role = Role(name='user')
        super_user_role = Role(name='superuser')
        db.session.add(user_role)
        db.session.add(super_user_role)
        db.session.commit()

        test_user = user_datastore.create_user(
            first_name='Admin',
            email='admin',
            password=encrypt_password('admin'),
            roles=[user_role, super_user_role]
        )'''


    # Start app
    app.run(debug=True)