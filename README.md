Participa
=========

Participa is envisioned as a powerful platform for enhancing communication between the public and the elected authorities. It is an on-going project writting in **python-django** and composed of several independent web applications. 

Cparte --the application available so far-- aims at enabling public institutions to stay informed about public opinions and priorities. Citizens post their opinions using social media hashtags and cparte delivers them in a measurable and structured way to the public instution (or authority) that is "listening" in the other side of the line.

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
