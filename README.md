Participa
=========

Improving democracy is probably one of today’s most challenging public concern. Motivated by the [Open Government](https://petitions.whitehouse.gov) 
efforts of the Obama’s administration, an increasing number of governments, public institutions, politicians and 
civic organizations have started making significant efforts toward more inclusive, transparent and participatory 
administrations. In this sense, technology has been playing a crucial role as a facilitator of the ever-growing initiatives that 
seek to involve citizens in public consultations and decision-making processes oriented to address public interest issues, 
such as law reforms and innovations in the public sector. 

In this context and boosted by the World Wide Web, online civic-engagement practices have been appearing all over the world. Reaching a 
large and diverse group of participants is key to success in such initiatives. However, most of state of art civic-participation 
tools work practically independent from today's biggest online communities found in social networking sites, such as Facebook, 
Twitter, or Google Plus.  

**Participa** is a platform created to facilitate public institutions, politicians, and elected authorities the execution of
public consultants, idea campaigns, and opinion polls directly in social networking sites. It allows to organize civic 
participation initiatives under a flexible structure that enables to efficiently aggregate, process and make sense of citizens' 
opinions, ideas, and suggestions generated during these initiatives. 

It is social network "agnostic" making possible to reach different social network communities simultaneously, which favors
inclusiveness and diversity. It can be used as a stand-alone application or it can be integrated with existing 
tools to enrich and complement active civic participation initiatives with the expertise, knowledge, and opinions 
of social network communities.


Conceptual Model
----------------
The general purpose **social networks** are the main instrument in which participa is based on. It exploits the power
and advantages (free, user-friendliness, worldwide connectivity, real-time information sharing) of these means to reach and 
engage the biggest virtual communities into online civic participation initiatives. 

The functioning of participa is based on **hashtags**, these are the key elements on which the initiatives supported by 
participa leverage on. Because of this, it can work only with hashtag-supported social networking sites, such as Twitter,
Facebook, Google Plus, and Instagram. Currently, *only Twitter is available*.

The remaining concepts of participa's model are the initiatives, campaigns, and challenges, which all are logically
related. The **initiatives** are the elements in which the details about the public consultants are defined. In the initiative
the organizer, e.g. public institutions, elected authorities, politician, civic organizations, set the hashtag that will
allow to identify the consultant and the social network in which the consultant will be run. To avoid error collecting the 
posts related to the consultant the initiative hashtag should be chosen carefully. In participa, each initiative is composed of 
one or more **campaigns**, which are the phases or stages in which a consultant is divided in. Finally, campaigns contain
**challenges**, which are the questions, topics, or issues on which the consultant is based on. 

Further, it is included the explanation of real use case scenario to ground the concepts.
  

How is it work?
---------------

Participa's operation is divided in four simple steps as it is outlined in the following picture. 

![model](https://dl.dropboxusercontent.com/u/55956367/participa_model.png "Participa Model")

1. A public institution (politician, elected authority, civic organization) creates an initiative, its corresponding 
campaigns and challenges, and the hashtags to be used.
2. The initiative's organizer (a public institution in this case) "deploys" the initiative in one or multiple social networks.
3. Citizens, which are users of the social networks where the initiative was deployed, engage by publishing posts 
containing the hashtags of the initiative and the challenge that are answering.
4. As soon as participa finds posts containing the hashtags of the initiative and challenges, it collects, processes them. 
Through a tabular-based dashboard the answers are presented to the initiative's organizer. Features to graphically 
represent the answers are upcoming. While setting the initiative, the organizer can program the platform to send the collected 
opinions/ideas/suggestions to an external platform.

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

Technology
----------

1. [Django Framework > 1.7](https://www.djangoproject.com/) `pip install Django`
2. [MySQL](http://www.mysql.com) database and its corresponding python package `pip install MySQL-python`
3. [Tweepy](http://www.tweepy.org) a python-based Twitter API client `pip install tweepy`
4. [Django Admin Bootstrapped](https://riccardo.forina.me/bootstrap-your-django-admin-in-3-minutes) App `pip install django-admin-bootstrapped`
5. [Django Bootstrap3](https://github.com/dyve/django-bootstrap3) App `pip install django-bootstrap3`
6. [Google API Client](https://developers.google.com/api-client-library/python/) `pip install google-api-python-client`
7. [Celery](http://www.celeryproject.org) `pip install celery`
8. [Celery for Django](http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html) `pip install django-celery`
9. [Rabbit MQ](http://www.rabbitmq.com/install-generic-unix.html)