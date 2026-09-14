from django.contrib.auth import get_user_model
from opportunities.models import Opportunity
from applications.models import Application
from engagements.models import EngagementRecord

User = get_user_model()

# Delete old test users if they exist
User.objects.filter(email='enabler@test.com').delete()
User.objects.filter(email='volunteer@test.com').delete()

# Create enabler user
enabler = User.objects.create_user(
    username='Test Organization',
    email='enabler@test.com',
    password='password123!',
    role='enabler'
)

# Create pathfinder user
pathfinder = User.objects.create_user(
    username='Jane Doe Volunteer',
    email='volunteer@test.com',
    password='password123!',
    role='pathfinder'
)

# Create opportunity
opp = Opportunity.objects.create(
    created_by=enabler,
    title='Community Coastal Cleanup Coordinator',
    description='Lead the weekend cleanup drives on the coast.',
    opportunity_type='volunteering',
    link='https://example.com/coastal-cleanup',
    is_open=True,
    role_skill_tags=['Environment', 'Leadership', 'Teamwork']
)

# Accept Application directly to trigger EngagementRecord
app = Application.objects.create(
    opportunity=opp,
    user=pathfinder,
    status='accepted'
)

print(f"\n--- SUCCESS ---")
print(f"Created Opportunity: {opp.title}")
print(f"Engagement Created: {EngagementRecord.objects.filter(opportunity=opp).exists()}")
print(f"\nTest Accounts Created:")
print(f"Organization (Enabler) Login: enabler@test.com / password123!")
print(f"Volunteer (Pathfinder) Login: volunteer@test.com / password123!")
