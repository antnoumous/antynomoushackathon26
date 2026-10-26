def test_recorder_counts_actual_attempts_fallbacks_and_per_schema():
    from app.generation_status import GenerationOutcome,GenerationRecorder
    rec=GenerationRecorder("meterless")
    assert rec.summary()["status"] == "not_used"
    rec.record(GenerationOutcome("finding_claim","meterless","meterless","meterless/local",True,False,None,0.1))
    rec.record(GenerationOutcome("run_summary","meterless","rules",None,False,True,"configuration",0.0))
    result=rec.summary()
    assert (result["attempts"],result["successes"],result["fallbacks"],result["status"]) == (1,1,1,"partial")
    assert result["schemas"]["finding_claim"] == {"attempts":1,"successes":1,"fallbacks":0}
    assert result["models"] == ["meterless/local"]
    assert len(rec.outcomes()) == 2
    assert GenerationRecorder("meterless").outcomes() == ()


def test_recorder_refuses_nonfinite_or_contradictory_outcomes_without_echoing_values():
    from dataclasses import replace
    import pytest
    from app.generation_status import GenerationOutcome,GenerationRecorder
    row=GenerationOutcome("verdict_reason","meterless","meterless","meterless/local",True,False,None,0.1)
    for change in [{"latency_s":float("nan")},{"latency_s":float("inf")},{"latency_s":-1},
                   {"actual_backend":"private-token"},{"category":"private-token"},
                   {"attempted":False},{"fallback":True},{"configured_provider":"rules"}]:
        rec=GenerationRecorder("meterless")
        with pytest.raises(ValueError) as caught:rec.record(replace(row,**change))
        assert "private-token" not in str(caught.value)
        assert rec.outcomes() == ()
