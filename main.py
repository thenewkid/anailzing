#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from flask import Flask, redirect, render_template, request, jsonify, url_for
from gaesessions import get_current_session
from google.appengine.api import users
from google.appengine.ext import ndb
from datetime import datetime
import hmac
import jinja2
import os
import json
import logging
import time

# flask app and jinja2 settings
def create_flask_app():
    app = Flask(__name__)
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)
    app.jinja_env = jinja_env
    app.debug = True
    return app


app = create_flask_app()


@app.route("/")
def index():
    session = get_current_session()
    if session.get("authenticated"):
        return redirect("/profile")
    return render_template("index.html")


@app.route("/login", methods=["post"])
def login():
    try:
        username = str(request.form["username"])
        password = str(request.form["password"])

        exists, user = User.user_exists(username, password)
        if exists:
            session = get_current_session()
            session["authenticated"] = True
            session["username"] = username
            user.add_recent_visit()
            return redirect(url_for("profile"))

        else:
            return redirect(url_for("index"))

    except Exception as e:
        return str(e)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/testimonials")
def testimonials():
    return render_template("testimonials.html", testimonials=Testimonial.get_testimonials())


@app.route("/submit_testimonial", methods=["post"])
def submit_testimonial():
    author = str(request.form["author"])
    message = str(request.form["message"])
    Testimonial.create_testimonial(author, message)
    testimonials = Testimonial.get_testimonials()
    return render_template("testimonials.html", success=True, testimonials=testimonials)


@app.route("/signup", methods=["post"])
def signup():
    try:
        username = str(request.form["username"])
        password = str(request.form["password"])

        if User.username_taken(username):
            return render_template("index.html", message="Username is taken", error=True)
        else:
            User.create_user(username, password)
            time.sleep(1)
            user = User.query(User.username == username).get()
            user.add_recent_visit()
            get_current_session()["authenticated"] = True
            get_current_session()["username"] = username
            return redirect(url_for("profile"))

    except Exception as e:
        logging.info(str(e))


@app.route("/profile")
def profile():
    try:
        session = get_current_session()
        if not session.get("authenticated"):
            return redirect(url_for("index"))
        else:
            time.sleep(1)
            recent_visits = User.get_recent_visits(session.get("username"))
            appointments = Appointment.get_appointments(session.get("username"))

            error = request.args.get("error")
            return render_template("profile.html", username=session.get("username"), recent_visits=recent_visits, appointments=appointments, error=error)
    except Exception as e:
        logging.info(str(e))


@app.route("/logout")
def logout():
    session = get_current_session()
    if session.get("authenticated"):
        session["authenticated"] = False
        session.clear()
    return redirect(url_for("index"))


@app.route("/schedule_appointment", methods=["post"])
def schedule_appointment():
    session = get_current_session()
    type = request.form["type"]
    date = request.form["date"]
    utc_dt = datetime.strptime(date, '%Y-%m-%dT%H:%M')
    timestamp = (utc_dt - datetime(1970, 1, 1)).total_seconds()
    if Appointment.time_exists(str(timestamp), session.get("username")):
        return redirect("/profile?error=time")
    Appointment.create_appointment(type, str(timestamp), session.get("username"))
    time.sleep(1)
    return redirect("/profile")



class User(ndb.Expando):
    username = ndb.StringProperty()
    password = ndb.StringProperty()
    recent_visits = ndb.StringProperty(repeated=True)

    @classmethod
    def user_exists(cls, un, pw):
        user_query = cls.query(cls.username == un, cls.password == hash_password(pw))
        single_user = user_query.get()
        exists = single_user != None
        return exists, single_user

    @classmethod
    def username_taken(cls, un):
        user = cls.query(cls.username == un).get()
        return user is not None

    @classmethod
    def create_user(cls, un, pw):
        user = User(
            username=un,
            password=hash_password(pw)
        )
        user.put()

    @classmethod
    def get_recent_visits(cls, username):
        return cls.query(cls.username == username).get().recent_visits

    def add_recent_visit(self):
        self.recent_visits.append(str(int(time.time())))
        self.put()


class Testimonial(ndb.Expando):
    author = ndb.StringProperty()
    message = ndb.TextProperty()

    @classmethod
    def get_testimonials(cls):
        return cls.query().fetch()

    @classmethod
    def create_testimonial(cls, author, message):
        t = Testimonial(
            author=author,
            message=message
        )
        t.put()


class Appointment(ndb.Expando):
    type = ndb.StringProperty()
    appointment_time = ndb.StringProperty()
    username = ndb.StringProperty()

    @classmethod
    def create_appointment(cls, type, time, username):
        new_appointment = Appointment(
            type=type,
            appointment_time=time,
            username=username
        )
        new_appointment.put()

    @classmethod
    def get_appointments(cls, username):
        return cls.query(cls.username == username).fetch()

    @classmethod
    def time_exists(cls, timestamp, username):
        return cls.query(cls.appointment_time == timestamp and cls.username == username).get() is not None

def hash_password(password):
    return hmac.new(password).hexdigest()
