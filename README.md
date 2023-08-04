# sliver
this multistrategy, multimarket proof of concept trading platform is made of three main components:
* [frontend](https://github.com/rbmarliere/sliver/tree/master/web) with a dynamic client-side backtesting feature where the user can choose strategies to subscribe, create new ones and set his general parameters;
* a [REST http api](https://github.com/rbmarliere/sliver/tree/master/src/sliver/api) the frontend consumes to interact with the backend database
* the async [watchdog](https://github.com/rbmarliere/sliver/blob/master/src/sliver/watchdog.py) daemon that updates each strategy and take trading actions on behalf of its subscribed users

### watchdog sample log
![20230804165808](https://github.com/rbmarliere/sliver/assets/6377318/96717ccd-8cb7-455d-afc1-b722e695929d)

### frontend sample strategy backtesting summary
![20230804170244](https://github.com/rbmarliere/sliver/assets/6377318/44580884-0885-4feb-af6e-e0d3250053d7)
![20230804170346](https://github.com/rbmarliere/sliver/assets/6377318/7198791f-525f-4df8-9504-2a1832d6e831)
