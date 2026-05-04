"""
GRAP Mapping Service - AI-Powered Account Mapping Suggestions
Provides intelligent suggestions for mapping balance sheet accounts to GRAP categories
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

@dataclass
class MappingSuggestion:
    """Represents a GRAP mapping suggestion with confidence score"""
    category_code: str
    category_name: str
    confidence: float
    reason: str
    alternative_matches: List[str]

class GRAPMappingService:
    """AI-powered service for suggesting GRAP category mappings"""
    
    def __init__(self):
        self.grap_categories = self._load_grap_categories()
        self.keyword_mappings = self._build_keyword_mappings()
        self.pattern_matches = self._build_pattern_matches()
    
    def _load_grap_categories(self) -> Dict[str, Dict]:
        """Load GRAP categories with their keywords and patterns"""
        return {
            # ASSETS
            'CA100': {
                'name': 'Cash and Cash Equivalents',
                'keywords': ['cash', 'bank', 'petty cash', 'money market', 'equivalents', 'liquid assets'],
                'patterns': [r'cash.*account', r'bank.*account', r'money.*market'],
                'examples': ['Cash on Hand', 'Bank Account', 'Petty Cash']
            },
            'CA110': {
                'name': 'Investments',
                'keywords': ['investment', 'securities', 'bonds', 'shares', 'equity', 'portfolio'],
                'patterns': [r'investment.*account', r'securit', r'bond.*invest'],
                'examples': ['Investment Securities', 'Government Bonds', 'Share Investments']
            },
            'CA120': {
                'name': 'Receivables',
                'keywords': ['receivable', 'debtors', 'accounts receivable', 'trade receivable'],
                'patterns': [r'receivable', r'debtor', r'account.*receivable'],
                'examples': ['Trade Receivables', 'Other Receivables', 'Government Receivables']
            },
            'CA130': {
                'name': 'Inventories',
                'keywords': ['inventory', 'stock', 'goods', 'materials', 'supplies'],
                'patterns': [r'inventory', r'stock.*account', r'material.*account'],
                'examples': ['Inventory of Goods', 'Raw Materials', 'Work in Progress']
            },
            'CA140': {
                'name': 'Other Current Assets',
                'keywords': ['prepaid', 'current', 'short term', 'accrued'],
                'patterns': [r'prepaid', r'accrued', r'current.*asset'],
                'examples': ['Prepaid Expenses', 'Accrued Income', 'Other Current Assets']
            },
            'CA150': {
                'name': 'Non-Current Financial Assets',
                'keywords': ['non-current', 'long term', 'financial asset', 'investment'],
                'patterns': [r'non.*current', r'long.*term', r'financial.*asset'],
                'examples': ['Long-term Investments', 'Financial Assets', 'Other Non-current Assets']
            },
            'CA160': {
                'name': 'Property, Plant and Equipment',
                'keywords': ['property', 'plant', 'equipment', 'ppe', 'fixed asset'],
                'patterns': [r'property.*plant', r'plant.*equipment', r'fixed.*asset'],
                'examples': ['Land and Buildings', 'Plant and Equipment', 'Motor Vehicles']
            },
            'CA170': {
                'name': 'Intangible Assets',
                'keywords': ['intangible', 'goodwill', 'software', 'patent', 'trademark'],
                'patterns': [r'intangible', r'goodwill', r'software.*asset'],
                'examples': ['Software', 'Goodwill', 'Patents and Trademarks']
            },
            'CA180': {
                'name': 'Investment Property',
                'keywords': ['investment property', 'rental', 'property investment'],
                'patterns': [r'investment.*property', r'rental.*property'],
                'examples': ['Investment Property', 'Rental Properties']
            },
            
            # LIABILITIES
            'CL200': {
                'name': 'Payables',
                'keywords': ['payable', 'creditors', 'accounts payable', 'trade payable'],
                'patterns': [r'payable', r'creditor', r'account.*payable'],
                'examples': ['Trade Payables', 'Other Payables', 'Tax Payables']
            },
            'CL210': {
                'name': 'Provisions',
                'keywords': ['provision', 'contingent', 'liability', 'reserve'],
                'patterns': [r'provision', r'contingent', r'reserve.*liability'],
                'examples': ['Provision for Leave', 'Provision for Bad Debts', 'Other Provisions']
            },
            'CL220': {
                'name': 'Non-Current Liabilities',
                'keywords': ['non-current', 'long term', 'long-term liability'],
                'patterns': [r'non.*current.*liab', r'long.*term.*liab'],
                'examples': ['Long-term Borrowings', 'Deferred Tax Liabilities', 'Other Non-current Liabilities']
            },
            'CL230': {
                'name': 'Retirement Benefits',
                'keywords': ['pension', 'retirement', 'post-employment', 'superannuation'],
                'patterns': [r'pension', r'retirement', r'superannuation'],
                'examples': ['Pension Fund', 'Post-employment Benefits', 'Retirement Annuities']
            },
            
            # EQUITY
            'EQ300': {
                'name': 'Capital and Reserves',
                'keywords': ['capital', 'reserves', 'retained', 'accumulated', 'equity'],
                'patterns': [r'capital.*account', r'reserve.*account', r'retained.*earning'],
                'examples': ['Share Capital', 'Retained Earnings', 'Other Reserves']
            },
            
            # REVENUE
            'RV400': {
                'name': 'Revenue',
                'keywords': ['revenue', 'income', 'fees', 'grants', 'subsidies'],
                'patterns': [r'revenue', r'income.*account', r'fee.*income'],
                'examples': ['Service Revenue', 'Grants and Subsidies', 'Other Revenue']
            },
            
            # EXPENSES
            'EX500': {
                'name': 'Expenses',
                'keywords': ['expense', 'cost', 'expenditure', 'operating', 'administrative', 'salaries', 'wages', 'office', 'supplies', 'software', 'licenses', 'rent', 'utilities', 'maintenance', 'training', 'travel', 'marketing', 'consulting', 'legal', 'insurance', 'taxes', 'depreciation', 'amortisation'],
                'patterns': [r'expense', r'cost.*account', r'expenditure', r'salar', r'wage', r'office.*suppl', r'software', r'license', r'rent', r'utilit', r'mainten', r'train', r'travel', r'market', r'consult', r'legal', r'insur', r'tax', r'depreci', r'amortis'],
                'examples': ['Employee Costs', 'Operating Expenses', 'Depreciation and Amortisation', 'Salaries - Finance', 'Office Supplies', 'Software Licenses', 'Rent Expense', 'Utilities', 'Training Costs', 'Travel Expenses']
            }
        }
    
    def _build_keyword_mappings(self) -> Dict[str, List[str]]:
        """Build keyword to category mappings"""
        keyword_map = {}
        for category_code, category_data in self.grap_categories.items():
            for keyword in category_data['keywords']:
                keyword_map[keyword.lower()] = category_code
        return keyword_map
    
    def _build_pattern_matches(self) -> List[Tuple[str, str, str]]:
        """Build regex pattern matches for categories"""
        pattern_matches = []
        for category_code, category_data in self.grap_categories.items():
            for pattern in category_data['patterns']:
                pattern_matches.append((category_code, pattern, category_data['name']))
        return pattern_matches
    
    def _preprocess_account_description(self, account_name: str) -> str:
        """Preprocess account description for better matching"""
        if not account_name:
            return ""
        
        # Convert to lowercase and strip
        processed = account_name.lower().strip()
        
        # Remove common prefixes/suffixes that don't add meaning
        prefixes_to_remove = ['acct:', 'account:', 'code:', 'dept:', 'department:']
        suffixes_to_remove = [' - dept', ' - department', ' (dept)', ' (department)']
        
        for prefix in prefixes_to_remove:
            if processed.startswith(prefix):
                processed = processed[len(prefix):].strip()
        
        for suffix in suffixes_to_remove:
            if processed.endswith(suffix):
                processed = processed[:-len(suffix)].strip()
        
        # Handle department format like "Salaries - Finance" -> "salaries finance"
        if ' - ' in processed:
            parts = processed.split(' - ')
            if len(parts) >= 2:
                # Keep both parts but reorder for better keyword matching
                main_desc = parts[0].strip()
                dept = parts[1].strip()
                processed = f"{main_desc} {dept}"
        
        # Remove extra whitespace
        processed = ' '.join(processed.split())
        
        return processed
    
    def calculate_match_score(self, account_name: str, account_code: str, category_code: str) -> float:
        """Calculate confidence score for account-category match"""
        # Use preprocessing for better matching
        account_name_clean = self._preprocess_account_description(account_name)
        account_code_clean = account_code.lower().strip()
        
        score = 0.0
        
        # Exact keyword matches (highest weight)
        category_keywords = self.grap_categories[category_code]['keywords']
        for keyword in category_keywords:
            if keyword in account_name_clean:
                score += 0.4
        
        # Partial keyword matches (medium weight)
        for keyword in category_keywords:
            if keyword in account_name_clean or account_name_clean in keyword:
                score += 0.2
        
        # Pattern matches (medium weight)
        for pattern in self.grap_categories[category_code]['patterns']:
            if re.search(pattern, account_name_clean, re.IGNORECASE):
                score += 0.3
        
        # Fuzzy string matching (low weight)
        matcher = SequenceMatcher(None, account_name_clean)
        category_name_clean = self.grap_categories[category_code]['name'].lower()
        ratio = matcher.ratio()
        if ratio > 0.6:
            score += ratio * 0.1
        
        # Account code matching (medium weight)
        code_matcher = SequenceMatcher(None, account_code_clean)
        for example in self.grap_categories[category_code]['examples']:
            example_clean = example.lower()
            if code_matcher.ratio() > 0.7:
                score += 0.25
        
        # Bonus for department-specific descriptions (like "Salaries - Finance")
        if ' - ' in account_name:
            parts = account_name.split(' - ')
            if len(parts) >= 2:
                # Give extra weight if we can match both parts
                main_desc = parts[0].strip().lower()
                dept = parts[1].strip().lower()
                
                for keyword in category_keywords:
                    if keyword in main_desc:
                        score += 0.1  # Bonus for main description match
                    if keyword in dept:
                        score += 0.05  # Small bonus for department match
        
        # Normalize score to 0-1 range
        return min(score, 1.0)
    
    def get_mapping_suggestions(self, account_name: str, account_code: str, top_n: int = 3) -> List[MappingSuggestion]:
        """Get top N mapping suggestions for an account"""
        suggestions = []
        
        for category_code, category_data in self.grap_categories.items():
            confidence = self.calculate_match_score(account_name, account_code, category_code)
            
            if confidence > 0.3:  # Minimum confidence threshold
                reason = self._generate_match_reason(account_name, account_code, category_code, confidence)
                
                suggestion = MappingSuggestion(
                    category_code=category_code,
                    category_name=category_data['name'],
                    confidence=confidence,
                    reason=reason,
                    alternative_matches=self._get_alternative_matches(account_name, category_code)
                )
                suggestions.append(suggestion)
        
        # Sort by confidence score (descending)
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return suggestions[:top_n]
    
    def _generate_match_reason(self, account_name: str, account_code: str, category_code: str, confidence: float) -> str:
        """Generate human-readable reason for the match"""
        category_data = self.grap_categories[category_code]
        account_name_clean = account_name.lower().strip()
        
        reasons = []
        
        # Check for keyword matches
        for keyword in category_data['keywords']:
            if keyword in account_name_clean:
                reasons.append(f"Contains keyword '{keyword}'")
        
        # Check for pattern matches
        for pattern in category_data['patterns']:
            if re.search(pattern, account_name_clean, re.IGNORECASE):
                reasons.append("Matches pattern")
        
        # Check for fuzzy matches
        matcher = SequenceMatcher(None, account_name_clean)
        category_name_clean = category_data['name'].lower()
        if matcher.ratio() > 0.7:
            reasons.append("Similar to category name")
        
        if not reasons:
            reasons.append("General similarity match")
        
        return "; ".join(reasons[:2])  # Limit to top 2 reasons
    
    def _get_alternative_matches(self, account_name: str, category_code: str) -> List[str]:
        """Get alternative category matches for the same account"""
        alternatives = []
        account_name_clean = account_name.lower().strip()
        
        # Find other categories with significant overlap
        for alt_code, alt_data in self.grap_categories.items():
            if alt_code == category_code:
                continue
            
            alt_confidence = self.calculate_match_score(account_name, "", alt_code)
            if alt_confidence > 0.5:  # Significant alternative match
                alternatives.append(f"{alt_data['name']} ({alt_confidence:.0%})")
        
        return alternatives[:2]  # Top 2 alternatives
    
    def batch_get_suggestions(self, accounts: List[Dict], top_n: int = 3) -> Dict[str, List[MappingSuggestion]]:
        """Get suggestions for multiple accounts at once"""
        results = {}
        
        for account in accounts:
            account_id = account.get('id', account.get('account_id', ''))
            account_name = account.get('name', account.get('description', ''))
            account_code = account.get('code', '')
            
            if account_id and account_name:
                suggestions = self.get_mapping_suggestions(account_name, account_code, top_n)
                results[account_id] = suggestions
        
        return results
    
    def auto_map_accounts(self, accounts: List[Dict], confidence_threshold: float = 0.7) -> Dict[str, str]:
        """Automatically map accounts with high confidence"""
        auto_mappings = {}
        
        for account in accounts:
            account_id = account.get('id', account.get('account_id', ''))
            account_name = account.get('name', account.get('description', ''))
            account_code = account.get('code', '')
            
            if account_id and account_name:
                suggestions = self.get_mapping_suggestions(account_name, account_code, top_n=1)
                
                if suggestions and suggestions[0].confidence >= confidence_threshold:
                    auto_mappings[account_id] = suggestions[0].category_code
        
        return auto_mappings
    
    def validate_mapping(self, account_name: str, account_code: str, suggested_category: str) -> Dict:
        """Validate a mapping and provide feedback"""
        suggestion = self.get_mapping_suggestions(account_name, account_code, top_n=1)
        
        if not suggestion:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'message': 'No suitable GRAP category found',
                'suggestions': []
            }
        
        top_suggestion = suggestion[0]
        is_correct = top_suggestion.category_code == suggested_category
        
        return {
            'is_valid': is_correct,
            'confidence': top_suggestion.confidence,
            'message': f"Mapping is {'correct' if is_correct else 'incorrect'}",
            'suggested_category': top_suggestion.category_code,
            'suggested_name': top_suggestion.category_name,
            'reason': top_suggestion.reason,
            'alternatives': top_suggestion.alternative_matches if not is_correct else [],
            'all_suggestions': suggestion,
            'issues': [] if is_correct else ['Category may not be optimal for this account type']
        }
    
    def get_category_details(self, category_code: str) -> Optional[Dict]:
        """Get detailed information about a GRAP category"""
        return self.grap_categories.get(category_code)
    
    def search_categories(self, query: str) -> List[Dict]:
        """Search GRAP categories by name or keywords"""
        query_clean = query.lower().strip()
        results = []
        
        for category_code, category_data in self.grap_categories.items():
            # Search in category name
            if query_clean in category_data['name'].lower():
                results.append({
                    'code': category_code,
                    'name': category_data['name'],
                    'match_type': 'name',
                    'keywords': category_data['keywords'],
                    'examples': category_data['examples']
                })
                continue
            
            # Search in keywords
            for keyword in category_data['keywords']:
                if query_clean in keyword:
                    results.append({
                        'code': category_code,
                        'name': category_data['name'],
                        'match_type': 'keyword',
                        'keywords': category_data['keywords'],
                        'examples': category_data['examples']
                    })
                    break
    def get_mapping_statistics(self) -> Dict:
        """Get statistics about current mappings"""
        return {
            'total_categories': len(self.grap_categories),
            'total_keywords': len(self.keyword_mappings),
            'total_patterns': len(self.pattern_matches)
        }

# Global instance
grap_mapping_service = GRAPMappingService()
