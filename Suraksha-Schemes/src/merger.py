import pandas as pd
import numpy as np

def smart_merge_text(text1, text2):
    if pd.isna(text1) or not text1: return text2
    if pd.isna(text2) or not text2: return text1
    
    t1_clean = str(text1).strip()
    t2_clean = str(text2).strip()
    
    if t1_clean == t2_clean:
        return t1_clean
        
    if t1_clean in t2_clean:
        return t2_clean
    if t2_clean in t1_clean:
        return t1_clean
        
    return f"Source 1:\n{t1_clean}\n\nSource 2:\n{t2_clean}"

def merge_datasets(my_df, hf_df):
    merged_records = []
    
    # 1. create dict of my_df by slug
    my_by_slug = {}
    my_by_name_state = {}
    
    for _, row in my_df.iterrows():
        r_dict = row.to_dict()
        slug = r_dict.get('slug')
        if slug and not pd.isna(slug):
            my_by_slug[slug] = r_dict
        else:
            name = str(r_dict.get('name', '')).lower()
            state = str(r_dict.get('state', '')).lower()
            key = f"{name}_{state}"
            my_by_name_state[key] = r_dict
            
    hf_handled = set()
    conflicts = []
    exact_matches = 0
    name_matches = 0
    
    # Match HF records
    for idx, hf_row in hf_df.iterrows():
        hf_dict = hf_row.to_dict()
        slug = hf_dict.get('slug')
        my_match = None
        
        if slug and not pd.isna(slug) and slug in my_by_slug:
            my_match = my_by_slug[slug]
            exact_matches += 1
            del my_by_slug[slug]
        else:
            name = str(hf_dict.get('name', '')).lower()
            state = str(hf_dict.get('state', '')).lower()
            key = f"{name}_{state}"
            if key in my_by_name_state:
                my_match = my_by_name_state[key]
                name_matches += 1
                del my_by_name_state[key]
                
        if my_match:
            # Merge logic
            merged = hf_dict.copy()
            # Combine texts
            merged['description'] = smart_merge_text(my_match.get('description'), hf_dict.get('description'))
            merged['eligibility_text'] = smart_merge_text(my_match.get('eligibility_text'), hf_dict.get('eligibility_text'))
            merged['benefits'] = smart_merge_text(my_match.get('benefits'), hf_dict.get('benefits'))
            merged['application_process'] = smart_merge_text(my_match.get('application_process'), hf_dict.get('application_process'))
            merged['documents_required'] = smart_merge_text(my_match.get('documents_required'), hf_dict.get('documents_required'))
            
            # Prefer MY for FAQs and Exclusions (HF doesn't have exclusions)
            merged['faqs'] = my_match.get('faqs') or hf_dict.get('faqs')
            merged['exclusions'] = my_match.get('exclusions') or hf_dict.get('exclusions')
            
            # Application mode from MY
            merged['application_mode'] = my_match.get('application_mode') or hf_dict.get('application_mode')
            
            # URLs
            merged['myscheme_url'] = hf_dict.get('myscheme_url') or my_match.get('myscheme_url')
            merged['official_external_url'] = my_match.get('official_external_url') or hf_dict.get('official_external_url')
            
            merged['source_provenance'] = 'gov_myscheme_data.csv, hf_schemes.csv'
            merged['verification_status'] = 'partially_verified'
            
            # Missing IDs/Slugs
            merged['slug'] = hf_dict.get('slug') or my_match.get('slug')
            merged['name'] = hf_dict.get('name') or my_match.get('name')
            
            merged_records.append(merged)
        else:
            merged_records.append(hf_dict)
            
    # Add remaining MY records
    for r in my_by_slug.values():
        merged_records.append(r)
    for r in my_by_name_state.values():
        merged_records.append(r)
        
    final_df = pd.DataFrame(merged_records)
    
    # Generate unique ID
    import uuid
    def gen_id(row):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, str(row['slug']) + str(row['name'])))
        
    final_df['scheme_id'] = final_df.apply(gen_id, axis=1)
    
    report = {
        'total_hf': len(hf_df),
        'total_my': len(my_df),
        'exact_matches': exact_matches,
        'name_matches': name_matches,
        'final_total': len(final_df)
    }
    
    return final_df, report
