# Notes

## Lex

### Input Event

- currentIntent

  - name
  - slots
  - confirmationStatus (prompt)

- userId (client)
- inputTranscript | inputText
- sessionAttribute

### Response Event

- dialogAction
  - type
  - intentName
  - slots
  - message
  - slotToElicit
  - responseCard
  - fulfillmentState
- sessionAttribute

## DynamoDB

- Partition Key (HashKey)
- SortKey (Composite Primary Key)

  - Partition Key
  - Sort Key

- Operation

  - Query
  - Scan
  - Filter

- Stream

## Lamdas

- Start at handler func

## Lex API

### Runtime

Itegrating bots in app

Has 2 actions

- PostContext

  - Text UTF-8
  - Speech
    - 16-8Hz
    - 1 channel
  - Return
    - Text or audio (MPEG,OGG,PCM)

- PostText

  - Text only
  - Response Card

### Model Building

- Create or gathering infos abot bot
- Make dynamic changes

### Chanel

- Amazon Connect
- Amazon Mobile Hub
- Amazon Echo
### Secure
* Cognito

### Gather Insights 
* Amazon Elasticsearch Service
* QuickSight
* AML

