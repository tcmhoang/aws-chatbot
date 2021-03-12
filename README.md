# Demo AWS Lex Chatbot

## Introduction

Amazon Lex is a service for building conversational interfaces into any application using voice and text.

It can be embedded in any website using a js snippet or server as a whole application

The project is integrated with some of AWS toolkits to build a dynamic bot with dynamic data without rebuilding the bot

## Services Used

- Lex (Chatbot)
- Lambda ( Handle further Initialization, Validation and Fulfillment)
- SNS ( Send SMS )
- Cloud Formation (Host Lex bot)
- S3 (Create buckets)
- DynamoDB (Query and Put data)
- IAM (Config roles and permisisons)
- CloudWatch (Log errors)
- Cognito (create pool)

## Trigger Intents

My Booking Movie Ticket Boot has 3 intents as listed below

### BookTickets

<figure align="center">
  <img src="./imgs/bt_u.png" />
  <figcaption>Utteraces</figcaption>
</figure>
<figure align="center">
  <img src="./imgs/bt_s.png" />
  <figcaption>Slots</figcaption>
</figure>

### GetTheater

<figure align="center">
  <img src="./imgs/gt_u.png" />
  <figcaption>Utteraces</figcaption>
</figure>
<figure align="center">
  <img src="./imgs/gt_s.png" />
  <figcaption>Slots</figcaption>
</figure>

### Help
Built-in Lex intent

## Lambda Function 
