Participa
=========

Improving democracy is probably one of today’s biggest societal challenges. Motivated by the [Open Government](https://petitions.whitehouse.gov) 
efforts of the Obama’s administration, an increasing number of governments, public institutions, politicians and 
civic organizations have started to take actions toward more inclusive, transparent and participatory administrations. 
In this context and boosted by the World Wide Web, online civic-engagement practices have been appearing all over the world
seeking to involve citizens in public consultations and decision-making processes oriented to address public interest issues, 
such as law reforms, policy making and innovations in the public sector. Reaching large and diverse groups of participants 
is key to success in such initiatives. 

Understanding that the biggest and diverse online communities are found in social networking sites, such as Facebook, 
Twitter, or Google Plus, we have created **participa** with the aim at supporting the execution of public consultants, 
idea campaigns, and opinion polls directly in social networking sites. It provides a flexible and generic model that
enables public institutions, politicians, and elected authorities to efficiently organize, run, the information generated 
during the civic participation initiatives. It is social network "agnostic" making possible to reach different social 
network communities simultaneously, favoring inclusiveness and diversity. It can be used as a stand-alone application or 
it can be integrated with existing tools to enrich and complement civic participation initiatives with the expertise, 
knowledge, and opinions of social network communities.


Conceptual Model
----------------
General purpose **social networks** are the main instrument in which participa is based on. It exploits the power
and advantages (user-friendliness, worldwide connectivity, real-time information sharing) of these means to reach and 
engage the biggest virtual communities into online civic participation initiatives. 

The functioning of participa is based on **hashtags**. Because of this, it can work only with hashtag-supported social 
networking sites, such as Twitter, Facebook, Google Plus, and Instagram. Currently, *only Twitter is available*.

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
Through a tabular-based dashboard the answers are presented to the initiative's organizer. In addition, participa can be 
programed to sinchronize its content with a remote platform.

Use Case
-----------

[California Report Card (CRC)](http://www.californiareportcard.org) is a jointly coordinated effort between the 
[Data and Democracy Initiative](http://citris-uc.org/initiatives/democracy/) of the Center for Information Technology Research 
in the Interest of Society (CITRIS) of the University of California, Berkeley and the Lt. Governor of California Gavin Newsom. 

By employing a web-based application, it engages citizens in discussion about public concern issues. Specifically, 
CRC allows to grade California in six timely topics and to to propose issues that merit the attention of the state 
government. The following picture illustrates CRC application. On the left, the alphabetical pad used to grade the pre-defined
topics, while on the right the section in which participants can suggest topics to be included in the next versions of CRC.

<img alt="CRC Screenshots" src="https://dl.dropboxusercontent.com/u/55956367/crc_screenshots.png" height="70%" width="70%" />

Participa is currently being used to enable citizens of California to grade CRC issues and to suggest news topics directly
via Twitter. In this context, the following elements were set up. California Report Card and *#careportcard* were defined 
as the **initiative** and the initiative **hashtag**, respectively. CRC is divided in two phases, the "grading" and the
"proposing", both were set as the **campaigns** of the initiatives. The CRC issues were configured as the **challenges** of
the grading campaign, each identified with a unique **hashtag**, while the request for a new issue, also associated with a
hashtag, was defined as the challenge of the proposing campaign. Finally, Twitter was chosen as the **social network** to deploy
the initiative.

The following picture shows participa in action. On the left, a participant grading the issue of CRC related with the affordability
of the state colleges and universities. For doing so, he attached to his grade the hashtag that identifies the initiative, 
**#careportcard**, and the hashtag associated to the issue, **#affordcolleges**. A similar approach was followed when proposing a new
issue. As depicted in the right side of the picture, the participant sent his suggestion together with the hashtag of the initiative
and the hashtag of the "performed" challenge, **#newissue**.

<img alt="CRC TW Screenshots" src="https://dl.dropboxusercontent.com/u/55956367/crc_tw_screenshots.png" height="70%" width="70%" />

Additional information on how to take part of CRC through Twitter can be found [here](https://dl.dropboxusercontent.com/u/55956367/Flyer_CRC_Twitter.pdf).

Installation
------------

1. Clone the repository `git clone https://github.com/joausaga/participa.git`

2. Go inside the repository folder and execute `pip install -r requirements.txt` to install dependencies 

3. Create a mysql database

4. Rename the file participa/settings.py.sample to participa/settings.py

5. Set the configuration parameters of the database in settings.py 

     ```
        DATABASES = {
            ...
                'NAME': '',
                'USER': '',
                'PASSWORD': '',
                'HOST': '',
                'PORT': '',
            ...
        }
      ```

6. Run `python manage.py migrate` to set up the database schema

7. Create a [Twitter application](https://apps.twitter.com) and give it read and write permissions

7. Rename the file cparte/config.sample to cparte/config

8. Set the Twitter application credentials in cparte/config

    ```
        [twitter_api]
        consumer_key = YOUR_TWITTER_APP_CONSUMER_KEY
        consumer_secret = YOUR_TWITTER_APP_CONSUMER_SECRET
        token = YOUR_TWITTER_APP_TOKEN
        token_secret = YOUR_TWITTER_APP_TOKEN_SECRET
    ```

9. Load initial settings `python manage.py loaddata config_data.json`

License
-------
MIT

Technologies
------------

1. [Django Framework > 1.7](https://www.djangoproject.com/)
2. [MySQL](http://www.mysql.com) database and its corresponding python package
3. [Tweepy](http://www.tweepy.org) a python-based Twitter API client
4. [Django Admin Bootstrapped App](https://riccardo.forina.me/bootstrap-your-django-admin-in-3-minutes)
5. [Django Bootstrap3 App](https://github.com/dyve/django-bootstrap3)
6. [Google API Client](https://developers.google.com/api-client-library/python/)
7. [Celery](http://www.celeryproject.org)
8. [Celery for Django](http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html)
9. [Rabbit MQ](http://www.rabbitmq.com/install-generic-unix.html)

Let me know
-----------

If you use participa, please [write me](mailto:jorgesaldivar@gmail.com) a short message with a link to your project. 
It is not mandatory, but I will really appreciate it!