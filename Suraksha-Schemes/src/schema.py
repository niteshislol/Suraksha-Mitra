import pandas as pd
import numpy as np
from src.cleaning import normalize_text, validate_url, deduplicate_list_str, safe_int, safe_bool

CANONICAL_COLUMNS = [
    "scheme_id",
    "slug",
    "name",
    "description",
    "level",
    "state",
    "ministry",
    "department",
    "category",
    "beneficiary_type",
    "eligibility_text",
    "eligibility_age_min",
    "eligibility_age_max",
    "eligibility_gender",
    "eligibility_caste",
    "eligibility_income_max",
    "eligibility_residence",
    "eligibility_state",
    "eligibility_disability",
    "eligibility_bpl",
    "exclusions",
    "benefits",
    "application_mode",
    "application_process",
    "documents_required",
    "faqs",
    "myscheme_url",
    "official_external_url",
    "apply_url",
    "source_provenance",
    "source_last_updated",
    "source_scraped_at",
    "last_verified_at",
    "verification_status"
]

def parse_level_and_state(row):
    level = normalize_text(row.get('Level'))
    state_ut_min = normalize_text(row.get('State / UT / Ministry'))
    
    state = None
    ministry = None
    
    if level:
        level_lower = level.lower()
        if 'state' in level_lower or 'ut' in level_lower:
            state = state_ut_min
        elif 'central' in level_lower:
            ministry = state_ut_min
    else:
        # fallback logic
        if state_ut_min and 'ministry' in state_ut_min.lower():
            level = 'Central'
            ministry = state_ut_min
        else:
            level = 'State'
            state = state_ut_min
            
    return pd.Series({'level': level, 'state': state, 'ministry': ministry})

def map_my_schema(df):
    canonical = pd.DataFrame(columns=CANONICAL_COLUMNS)
    if df.empty:
        return canonical
        
    def get_col(col_name):
        return df.get(col_name, pd.Series(index=df.index, dtype=object))
    
    canonical['slug'] = get_col('Scheme Slug').apply(normalize_text)
    canonical['name'] = get_col('Scheme Name').apply(normalize_text)
    
    level_info = df.apply(parse_level_and_state, axis=1)
    canonical['level'] = level_info['level']
    canonical['state'] = level_info['state']
    canonical['ministry'] = level_info['ministry']
    
    canonical['description'] = get_col('Description').apply(normalize_text)
    canonical['category'] = get_col('Tags / Categories').apply(normalize_text)
    
    # Combine eligibility text smartly
    el_criteria = get_col('Eligibility Criteria').apply(normalize_text)
    el_gen = get_col('Eligibility (General)').apply(normalize_text)
    
    def merge_el(c, g):
        if c and g and c != g:
            return f"{c}\n\nGeneral Eligibility:\n{g}"
        return c or g
    
    canonical['eligibility_text'] = [merge_el(c, g) for c, g in zip(el_criteria, el_gen)]
    
    canonical['exclusions'] = get_col('Exclusions / Ineligibility').apply(normalize_text)
    canonical['benefits'] = get_col('Benefits').apply(normalize_text)
    canonical['application_mode'] = get_col('Application Mode').apply(normalize_text)
    canonical['application_process'] = get_col('Application Process').apply(normalize_text)
    canonical['documents_required'] = get_col('Documents Required').apply(normalize_text)
    canonical['faqs'] = get_col('Frequently Asked Questions (FAQs)').apply(normalize_text)
    
    canonical['myscheme_url'] = get_col('MyScheme URL').apply(validate_url)
    canonical['official_external_url'] = get_col('Official Link').apply(validate_url)
    
    canonical['source_provenance'] = 'gov_myscheme_data.csv'
    canonical['verification_status'] = 'unverified'
    
    return canonical

def map_hf_schema(df):
    canonical = pd.DataFrame(columns=CANONICAL_COLUMNS)
    if df.empty:
        return canonical
        
    def get_col(col_name):
        return df.get(col_name, pd.Series(index=df.index, dtype=object))
        
    canonical['slug'] = get_col('slug').apply(normalize_text)
    canonical['name'] = get_col('name').apply(normalize_text)
    canonical['description'] = get_col('description').apply(normalize_text)
    canonical['ministry'] = get_col('ministry').apply(normalize_text)
    canonical['department'] = get_col('department').apply(normalize_text)
    canonical['state'] = get_col('state').apply(normalize_text)
    
    def determine_level(s):
        if not s: return None
        if str(s).lower().strip() == 'central': return 'Central'
        return 'State'
        
    canonical['level'] = get_col('state').apply(determine_level)
    canonical['state'] = canonical.apply(lambda row: None if row['level'] == 'Central' else row['state'], axis=1)
    
    canonical['category'] = get_col('category').apply(normalize_text)
    canonical['beneficiary_type'] = get_col('beneficiary_type').apply(normalize_text)
    canonical['eligibility_text'] = get_col('eligibility_text').apply(normalize_text)
    canonical['benefits'] = get_col('benefits').apply(normalize_text)
    canonical['application_process'] = get_col('application_process').apply(normalize_text)
    canonical['documents_required'] = get_col('documents_required').apply(normalize_text)
    
    canonical['apply_url'] = get_col('apply_url').apply(validate_url)
    canonical['myscheme_url'] = get_col('official_url').apply(validate_url)
    
    canonical['eligibility_age_min'] = get_col('eligibility_age_min').apply(safe_int)
    canonical['eligibility_age_max'] = get_col('eligibility_age_max').apply(safe_int)
    canonical['eligibility_gender'] = get_col('eligibility_gender').apply(normalize_text)
    
    canonical['eligibility_caste'] = get_col('eligibility_caste').apply(deduplicate_list_str)
    canonical['eligibility_income_max'] = get_col('eligibility_income_max').apply(safe_int)
    canonical['eligibility_residence'] = get_col('eligibility_residence').apply(normalize_text)
    canonical['eligibility_state'] = get_col('eligibility_state').apply(deduplicate_list_str)
    
    canonical['eligibility_disability'] = get_col('eligibility_disability').apply(safe_bool)
    canonical['eligibility_bpl'] = get_col('eligibility_bpl').apply(safe_bool)
    
    canonical['source_scraped_at'] = get_col('scraped_at').apply(normalize_text)
    canonical['source_provenance'] = 'hf_schemes.csv'
    canonical['verification_status'] = 'unverified'
    
    return canonical
