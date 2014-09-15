Participa
=========

Participa is envisioned as a powerful platform for enhancing communication between the public and the elected authorities. It is an on-going project writting in **python-django** and composed of several independent web applications. 

* *Cparte* --the only application available so far-- aims at enabling public institutions to stay informed about public opinions and priorities. Citizens post their opinions using social media hashtags and cparte delivers them in a measurable and structured way to the public instution (or authority) that is "listening" in the other side of the line.

Quick start
-----------

1. Add "cparte" to your INSTALLED_APPS setting like this:

      ```
      INSTALLED_APPS = (
          ...
          'cparte',
      )
      ```

2. Include the cparte URLconf in your project urls.py like this:

      `url(r'^cparte/', include('cparte.urls')),`

3. Run `python manage.py syncdb` to create cparte database schema.

Dependencies
------------

1. [Django Framework](https://www.djangoproject.com/) `pip install Django`
2. [MySQL](http://www.mysql.com) database and its corresponding python package `pip install MySQL-python`
3. [Tweepy](http://www.tweepy.org) a python-based Twitter API client `pip install tweepy`
4. [Django Admin Bootstrapped](https://riccardo.forina.me/bootstrap-your-django-admin-in-3-minutes) App `pip install django-admin-bootstrapped`
5. [Django Bootstrap3](https://github.com/dyve/django-bootstrap3) App `pip install django-bootstrap3`
6. [Google API Client](https://developers.google.com/api-client-library/python/) `pip install google-api-python-client`