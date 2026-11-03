"""Deterministic, auditable security agent. It advises; it cannot approve or query a DB."""
from __future__ import annotations
import time
from security_agent.catalog import CATALOG, validate_query

AGENT_VERSION='db-security-rules-v2'


class SecurityAgent:
    def __init__(self, scanner):
        self.scanner=scanner
        self.last_analysis_at=None

    def assess(self, arguments, principal, recent_requests=0, warning=100, block=600):
        errors=validate_query(arguments,principal)
        spec=CATALOG.get(arguments.get('dataset_id')) if isinstance(arguments.get('dataset_id'),str) else None
        requested=arguments.get('columns') if isinstance(arguments.get('columns'),list) else []
        sensitive=bool(spec and any(spec['columns'].get(c) in {'sensitive','restricted'} for c in requested if isinstance(c,str)))
        restricted=bool(spec and any(spec['columns'].get(c)=='restricted' for c in requested if isinstance(c,str)))
        row_limit=arguments.get('row_limit')
        bulk=type(row_limit) is int and row_limit>=1000
        purpose=arguments.get('purpose','')
        suspicious=bool(isinstance(purpose,str) and self.scanner(purpose))
        if suspicious:
            errors.append('SUSPICIOUS_INSTRUCTIONS')
        if recent_requests>=block:
            errors.append('ABNORMAL_REQUEST_RATE')
        abnormal=bool(errors) or recent_requests>=warning
        reasons=[]
        if sensitive:reasons.append('민감·고위험 열의 정보 조회를 요청했습니다.')
        if bulk:reasons.append(f'한 번에 {row_limit:,}행을 요청해 대량 조회 기준(1,000행)에 해당합니다.')
        if recent_requests>=warning:reasons.append(f'동일 에이전트의 최근 1분 요청이 {recent_requests}건으로 증가했습니다.')
        if errors:reasons.append('필수 정책 위반: '+', '.join(dict.fromkeys(errors)))
        if not reasons:reasons.append('등록된 데이터와 열, 조회량 범위 안의 읽기 요청입니다.')
        score=min(100,15+(55 if restricted else 35*int(sensitive))+25*int(bulk)+40*int(abnormal))
        decision='DENY' if errors else 'REQUIRE_APPROVAL'
        recommendation=('차단 유지. 요청 범위와 목적을 수정한 뒤 새로 요청하세요.' if errors else
            '범위를 줄인 새 요청을 요구하거나, 현재 범위의 업무 필요성이 확인될 때만 승인하세요.' if sensitive or bulk else
            '업무 목적과 요청자의 담당 범위를 확인한 뒤 일회성 조회를 승인하세요.')
        self.last_analysis_at=time.time()
        return {'engine':AGENT_VERSION,'method':'policy_and_behavior_rules','risk_score':score,
            'risk_level':'critical' if score>=80 else 'high' if score>=60 else 'medium' if score>=30 else 'low',
            'sensitive':sensitive,'bulk':bulk,'abnormal':abnormal,'reason_codes':list(dict.fromkeys(errors)),
            'reasons':reasons,'recommendation':recommendation,'decision':decision,
            'limitations':'정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.'}

    def health(self):
        sample={'dataset_id':'operations','columns':['ticket_id'],'filters':{},'row_limit':10,'purpose':'health probe for allowed data'}
        principal={'tenant':'north','role':'report-submitter'}
        previous=self.last_analysis_at
        started=time.perf_counter()
        try:
            benign=self.assess(sample,principal)
            unsafe=self.assess(dict(sample,row_limit=9000),principal)
            if benign['decision']!='REQUIRE_APPROVAL' or unsafe['decision']!='DENY':
                raise RuntimeError('분석 자체 점검의 예상 결정이 일치하지 않습니다.')
            return {'status':'up','engine':AGENT_VERSION,'checked_at':time.time(),'last_analysis_at':previous,
                    'latency_ms':round((time.perf_counter()-started)*1000,2),'detail':'정상·정책 위반 입력 분석 자체 점검 통과'}
        except Exception:
            return {'status':'down','engine':AGENT_VERSION,'checked_at':time.time(),'detail':'보안 분석 자체 점검 실패'}
        finally:
            self.last_analysis_at=previous
