# ops-dashboard

pnpm workspace with a Python 3.12 analytics service. CI runs on Ubuntu 24.04:
system Python 3.12, Node 20, pnpm. No pip on the image.

The analytics service's dependency pins (`services/analytics/requirements.txt`)
fail to resolve: ResolutionImpossible on numpy/scipy.
