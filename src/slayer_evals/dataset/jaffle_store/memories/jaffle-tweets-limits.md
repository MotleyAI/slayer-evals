---
created_at: '2026-11-06T10:40:21.038451Z'
description: 'tweets are templated and all positive: no sentiment analysis; use for
  volume and product mentions only'
entities:
- demo_database.tweets
- demo_database.tweets.content
- demo_database.tweets.tweet_count
version: 2
---
tweets.content is templated and uniformly positive ("Jaffles from the Jaffle Shop are {amazing|awesome|...}! Ordered a {product}."). It cannot support sentiment, complaint or satisfaction analysis: if asked, say the data cannot answer that rather than reporting 100% positive sentiment. It is valid for mention volume over time, the share of customers who post, and which products are named in posts.