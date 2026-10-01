from django.db import models


class FuelStation(models.Model):
    opis_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, db_index=True)
    price = models.FloatField(help_text="Retail price per gallon (USD)")
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["opis_id", "address", "city", "state"], name="uniq_station"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) ${self.price:.3f}"
