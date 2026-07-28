from django.db import models


class Vendor(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='vendor_profile')
    business_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    is_approved = models.BooleanField(default=False)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} ({'approved' if self.is_approved else 'pending'})"
