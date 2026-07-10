"""factory_boy factories for the speed_test app."""
import factory

from apps.analysis.constants import Strategy
from apps.analysis.tests.factories import AnalysisReportFactory, CompletedReportFactory
from apps.gtmetrix.tests.factories import (
    CompletedGTmetrixReportFactory,
    GTmetrixReportFactory,
)
from apps.speed_test.models import SpeedTest
from apps.users.tests.factories import UserFactory


class SpeedTestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SpeedTest

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.com")
    strategy = Strategy.MOBILE
    google_report = factory.SubFactory(AnalysisReportFactory)
    gtmetrix_report = factory.SubFactory(GTmetrixReportFactory)


class CompletedSpeedTestFactory(SpeedTestFactory):
    google_report = factory.SubFactory(CompletedReportFactory)
    gtmetrix_report = factory.SubFactory(CompletedGTmetrixReportFactory)
