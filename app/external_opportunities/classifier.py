"""
Keyword helpers that decide whether a scraped listing is a remote volunteer
role and which field (tech / business / marketing) it belongs to.
"""
import re

from opportunities.models import Opportunity

Field = Opportunity.Field

# Matched against the title, source career categories and description.
# Order matters: the first field with the most hits wins ties by this order.
FIELD_KEYWORDS = {
    Field.TECH: [
        'software', 'developer', 'development', 'engineer', 'programmer', 'programming',
        'web', 'mobile app', 'data', 'database', 'analytics', 'machine learning', 'ai',
        'cybersecurity', 'devops', 'cloud', 'ux', 'ui', 'information technology',
        'information and communications technology', 'ict', 'gis', 'qa', 'python', 'javascript',
    ],
    Field.MARKETING: [
        'marketing', 'social media', 'content', 'seo', 'communications', 'communication',
        'branding', 'copywriting', 'copywriter', 'graphic design', 'advocacy', 'campaign',
        'public relations', 'outreach', 'newsletter', 'video editing', 'storytelling',
    ],
    Field.BUSINESS: [
        'business', 'finance', 'financial', 'accounting', 'strategy', 'operations',
        'fundraising', 'grant writing', 'grant', 'project management', 'program management',
        'administration', 'consulting', 'consultant', 'human resources', 'hr', 'proposal',
        'monitoring and evaluation', 'fund development', 'partnerships',
    ],
}

VOLUNTEER_PATTERN = re.compile(r'\b(volunteer|volunteers|volunteering|pro[- ]?bono|unpaid)\b', re.I)
REMOTE_PATTERN = re.compile(
    r'\b(remote|remotely|online|home[- ]?based|virtual|work from home|telecommut\w*)\b', re.I
)


def _count_hits(text, keywords):
    return sum(1 for kw in keywords if re.search(rf'\b{re.escape(kw)}\b', text))


def classify_field(title, categories='', description=''):
    """
    Return a Field value, or None when nothing matches (the listing is skipped).
    The title and categories weigh more than the description.
    """
    primary = f'{title} {categories}'.lower()
    secondary = description.lower()

    best_field, best_score = None, 0
    for field, keywords in FIELD_KEYWORDS.items():
        score = 3 * _count_hits(primary, keywords) + _count_hits(secondary, keywords)
        if score > best_score:
            best_field, best_score = field, score
    return best_field


def is_volunteer(*texts):
    return any(VOLUNTEER_PATTERN.search(t or '') for t in texts)


def is_remote(*texts):
    return any(REMOTE_PATTERN.search(t or '') for t in texts)
