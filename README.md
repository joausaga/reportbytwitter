Participa
=========

Improving democracy is probably one of today’s most challenging public concern. Motivated by the Open Government efforts 
of the Obama’s administration, an increasing number of governments, public institutions, politicians and civic organizations 
have started making significant efforts toward more inclusive, transparent and participatory administrations. In this sense, 
technology is playing a crucial role as a facilitator of the ever-growing initiatives that seek to involve citizens in public
consultations and decision-making processes oriented to address public interest issues, such as law reforms and innovations 
in the public sector. 

In this context and boosted by the World Wide Web, online civic-engagement practices have been appearing all over the world. Reaching a 
large and diverse group of participants is key to success in such initiatives. However, most of state of art civic-participation 
tools work practically independent from today's biggest online communities found in social networking sites, such as Facebook, 
Twitter, or Google Plus.  

**Participa** is a platform created to facilitate public institutions/politicians/elected authorities the execution of
public consultants, idea campaigns, and opinion polls directly in social networking sites. It allows to organize civic 
participation initiatives under a flexible structure that enables to efficiently aggregate, process and make sense of citizens' 
opinions, ideas, and suggestions generated during these initiatives. 

It is social network "agnostic" making possible to reach different social network communities simultaneously, which favors
inclusiveness and diversity. It can be used as a stand-alone application or it can be integrated with already existing 
tools to enrich and complement already existing civic participation initiatives with the expertise, knowledge, and opinions 
of the biggest online communities present in social networks.


How is it work?
---------------

1. A public institution, government agency, or politician creates an initiative. campaign to collect opinions/ideas.  
2. The campaign is deployed in one or more hashtag-supported social networks. 
3. From that moment, every post published in the deployed social network(s) will be automatically gathered and aggregated.
4. 
 



only social networks' native features, 
like posts and hashtags. It is not another tool to advertise or promote civic participation initiatives inside social networks
nor a platform to  
 
 

. Citizens post their opinions using social media hashtags and 
cparte delivers them in a measurable and structured way to the public institution (or authority) that is "listening" in 
the other side of the line.

The extent of participation by the target people is key to success in nowadays internet-mediated
civic participation practices. Understanding that today's biggest online communities are found in social networking sites,  

However, most of them struggle to get large and diverse se tools all share the same limitation, they operate practically detached from 
the social networking sites, such Facebook, Twitter, Google Plus. Understanding that 



In this context, **Participa** has been created with the goal of involving the society at large into 

In this sense, if we want to attract people to democracy life we need to learn to engage them in their own terms. 
That it is to say, by employing the same technological systems, applications and platforms that they regularly use in their private life.  

Participa was created to is envisioned as a platform which ultimate goal is to enhance the communication between the public and the elected authorities.  

enabling citizens take part on public consultants through general purpose social networks. It allows

 It is an on-going project writting in **python-django** and composed of several independent web applications. 

* *cparte* --the only application available so far-- aims at enabling public institutions to stay informed about public opinions and priorities. Citizens post their opinions using social media hashtags and cparte delivers them in a measurable and structured way to the public institution (or authority) that is "listening" in the other side of the line.

Use Case
-----------

California Report Card

Installation
------------

1. Add "cparte" to your INSTALLED_APPS setting like this:

      ```
      INSTALLED_APPS = (
          ...
          'cparte',
      )
      ```

2. Include the cparte URLconf in your project urls.py like this:

      `url(r'^cparte/', include('cparte.urls')),`

3. Run `python manage.py migrate` to create cparte database schema.

4. Load initial settings `python manage.py loaddata config_data.json`

Dependencies
------------

1. [Django Framework > 1.7](https://www.djangoproject.com/) `pip install Django`
2. [MySQL](http://www.mysql.com) database and its corresponding python package `pip install MySQL-python`
3. [Tweepy](http://www.tweepy.org) a python-based Twitter API client `pip install tweepy`
4. [Django Admin Bootstrapped](https://riccardo.forina.me/bootstrap-your-django-admin-in-3-minutes) App `pip install django-admin-bootstrapped`
5. [Django Bootstrap3](https://github.com/dyve/django-bootstrap3) App `pip install django-bootstrap3`
6. [Google API Client](https://developers.google.com/api-client-library/python/) `pip install google-api-python-client`
7. [Celery](http://www.celeryproject.org) `pip install celery`
8. [Celery for Django](http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html) `pip install django-celery`
9. [Rabbit MQ](http://www.rabbitmq.com/install-generic-unix.html)