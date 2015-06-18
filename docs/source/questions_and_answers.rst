.. _questions_and_answers:

Q&A
===

Why did we call it Forseti?
---------------------------

We like to use gods names in our internal projects. We began using only norse gods, but currently we have also greek and roman gods. In the norse mythology, Forseti is "the presiding one" and we thought it has some coincidences with the purpose of this application. Forseti is the president of our applications, the utility which rules them all.

Why did you create Forseti instead of using other utilities or AWS official tools such as CloudFormation or CodeDeploy?
-----------------------------------------------------------------------------------------------------------------------

We began building Forseti in 2013 and in that time there were no AWS official tools nor an interface to EC2 Autoscale. There was a good API to create images, alarmas and autoscale groups but we missed an easy tool to mix everything. We did some research with [Netflix' asgard](https://github.com/Netflix/asgard) but it was a bit too much for us. So we started building Forseti to fit our needs and make it quick.
