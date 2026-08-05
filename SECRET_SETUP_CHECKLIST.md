# Secret Setup Checklist

- [ ] Massive.com API key copied from the Massive dashboard
- [ ] Lakebase password connections enabled
- [ ] Native password role created
- [ ] `GRANT CONNECT, CREATE` executed for the role
- [ ] Lakebase PostgreSQL URL copied with `sslmode=require`
- [ ] `python setup_secrets.py` completed
- [ ] `lakebase-url` added as App resource key `lakebase_url_secret`
- [ ] `massive-api-key` added as App resource key `massive_api_key_secret`
- [ ] App redeployed after resources were added
- [ ] Lakebase connection shows successful
- [ ] Massive API test completed or a plan-access error was understood
- [ ] Ticket create, message add, status update, and refresh persistence tested
