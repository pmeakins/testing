from django.db import models
from django.core.validators import RegexValidator

class Report(models.Model):
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?\d{1,15}$', message="Enter a valid phone number.")]
    )
    description = models.TextField(blank=True)
    trust_score = models.IntegerField(default=0)  # 0-100 score
    created_at = models.DateTimeField(auto_now_add=True)
    # Add more fields as needed, e.g., user_submitted = models.BooleanField(default=True)

    def __str__(self):
        return f"Report for {self.phone_number} - Score: {self.trust_score}"
