# GCP_Flask_Firebase

This is a simple API CRUD in FLASK + Firebase Demo

## The highlights are:
    - It was a quickly developed project/setup for showing base skills for developing
    - Currently only http errors such as 404 & 500 are handled with custom pages renders
    - This repo is connected with a Trigger in Google Cloud Build for automatic deploy after pushing changes 
    - Has the simple yet useful added logging configuration ofr showing logs in Google Cloud Run/Log Explorer

## Downside
    - Currently this lacks of any proper UI for managing the CRUD for a common final user, it's mostly likely for a developer with min experience with Restful APIs

### TODO
    - Add switch the frontend interface using VUE.js + Buefy UI and add controls for final users to use the api in the UI
    - Add example code for using Sendgrid by Twilio for validating emails validating format and validating 'A' and 'MX' DNS records
    - Add proper and documented Google Secrets usage for avoid exposing credentials
    - Add unittesting with pytest into the yaml file
    - Add Telegram realtime notifications
    - Add examples for APIs usage / flask-apispec
    - and ...

## Get hired

Last Update 2022 Jul 22 