# Metaprompt #3: WebGPU Research for Browser-Based TTS

**Task Type:** Comprehensive research via house-research agent
**Objective:** Evaluate feasibility of running Kokoro TTS in browser using WebGPU
**Output:** Detailed research report with recommendations
**Timeline:** Run separately, parallel to main development

---

## Research Overview

You are researching the feasibility and implementation approach for running **Kokoro TTS** (82M parameter model) in the browser using **WebGPU** technology. This is a high-risk, high-reward feature that would enable client-side TTS inference without server dependency.

Your research should produce a comprehensive report that informs the decision: **Should we implement WebGPU TTS in the MVP, defer to post-MVP, or skip entirely?**

---

## Context

### Current State:
- **Kokoro TTS**: 82M parameter model, PyTorch-based, MLX-optimized for Apple Silicon
- **Current Implementation**: Server-side Python inference via MLX
- **Target**: Browser-side inference using WebGPU API

### Why WebGPU TTS?
**Benefits:**
- No server load for TTS generation
- Faster response (no network latency)
- Privacy (audio never leaves client)
- Offline capability once model is cached
- Scales to unlimited users

**Challenges:**
- Browser compatibility limited
- Model size (~80MB download)
- Mobile device performance unknown
- Complex model conversion (PyTorch → ONNX → WebGPU)
- Untested with Kokoro specifically

### Decision Point:
If research shows WebGPU TTS is:
- **Viable with low complexity**: Include in MVP
- **Viable but complex**: Implement post-MVP
- **Not viable or too risky**: Skip, use server-side API

---

## Research Questions

### Section 1: WebGPU Browser Support (2025)

**Question 1.1: What is the current browser support for WebGPU API?**
- Which browsers support WebGPU (Chrome, Firefox, Safari, Edge)?
- Which versions are required?
- What is the market share of WebGPU-capable browsers?
- Mobile browser support (iOS Safari, Chrome Android)?
- Expected timeline for full browser support?

**Question 1.2: What are the performance characteristics?**
- Performance difference: WebGPU vs WebGL vs CPU
- GPU memory limits in browsers
- Performance on low-end devices
- Mobile vs desktop performance

**Question 1.3: What are known limitations?**
- API stability and maturity
- Known bugs or issues
- Browser-specific quirks
- Security/permission considerations

**Research Methods:**
- Check Can I Use (https://caniuse.com/webgpu)
- Check MDN Web Docs WebGPU status
- Review WebGPU implementation status on browser vendor sites
- Search for WebGPU performance benchmarks (2024-2025)

**Expected Output:**
```markdown
## WebGPU Browser Support Summary (2025)

### Support Matrix
| Browser | Version | Support Status | Notes |
|---------|---------|----------------|-------|
| Chrome  | 113+    | ✅ Stable      | ... |
| Edge    | 113+    | ✅ Stable      | ... |
| Safari  | 17+     | ⚠️ Partial     | ... |
| Firefox | 121+    | ⚠️ Beta        | ... |

### Market Share
- Percentage of users with WebGPU-capable browsers: X%
- Desktop vs mobile breakdown
- Geographic considerations

### Performance
- Typical inference speed: X tokens/sec
- GPU memory usage: X MB
- Mobile device performance: [findings]

### Limitations
1. [Major limitation 1]
2. [Major limitation 2]
...
```

---

### Section 2: ONNX Runtime Web + WebGPU

**Question 2.1: What is ONNX Runtime Web?**
- What is ONNX Runtime Web (ORT-Web)?
- How does it integrate with WebGPU?
- What is the performance compared to native PyTorch?
- What models has it been successfully used with?

**Question 2.2: Does ORT-Web support the operations Kokoro needs?**
- What neural network operations does Kokoro TTS use?
- Are all operations supported by ORT-Web + WebGPU?
- Are there known compatibility issues?
- What is the model size limit?

**Question 2.3: What is the implementation complexity?**
- How complex is the integration?
- What are the build/deployment requirements?
- Are there existing examples of TTS models in ORT-Web?
- What is the learning curve?

**Research Methods:**
- Read ONNX Runtime Web documentation
- Search for ORT-Web + WebGPU examples (GitHub, blogs)
- Check ONNX operator support list
- Look for TTS model examples (Tacotron, FastSpeech, etc.)
- Check Kokoro model architecture for operation types

**Expected Output:**
```markdown
## ONNX Runtime Web Analysis

### Overview
- ORT-Web version: X.X.X
- WebGPU execution provider: [status]
- Performance vs native: [findings]

### Operation Support
- Kokoro operations needed: [list]
- ORT-Web supported: ✅/❌ for each
- Workarounds for unsupported ops: [if any]

### Implementation Complexity
- Estimated development time: X weeks
- Required expertise: [list]
- Build/deployment complexity: Low/Medium/High
- Existing examples: [links]

### Recommendation
[Include/Defer/Skip] with reasoning
```

---

### Section 3: Model Conversion Pipeline

**Question 3.1: How to convert PyTorch → ONNX?**
- What is the PyTorch to ONNX export process?
- What tools are needed (torch.onnx.export)?
- What are common pitfalls?
- How to validate the conversion?

**Question 3.2: How to optimize ONNX for WebGPU?**
- What optimizations are available?
- Quantization options (INT8, FP16)?
- Model size vs quality trade-offs?
- Tools: ONNX Optimizer, ONNX Runtime tooling?

**Question 3.3: How to convert ONNX → WebGPU format?**
- Does ONNX Runtime Web handle this automatically?
- Or is additional conversion needed?
- What is the final model format?
- How is the model loaded in browser?

**Question 3.4: What is the expected model size?**
- Original Kokoro model: ~80MB (8-bit quantized)
- After ONNX conversion: X MB
- After WebGPU optimization: X MB
- Download time on typical connection: X seconds

**Research Methods:**
- Read PyTorch ONNX export documentation
- Read ONNX Runtime Web model format documentation
- Search for model conversion tutorials
- Check for Kokoro-specific conversion examples
- Research quantization techniques

**Expected Output:**
```markdown
## Model Conversion Analysis

### Conversion Pipeline
1. PyTorch (.pt) → ONNX (.onnx)
   - Tools: torch.onnx.export
   - Complexity: Low/Medium/High
   - Expected issues: [list]

2. ONNX Optimization
   - Quantization: INT8/FP16 options
   - Size reduction: X% → Y MB
   - Quality impact: [assessment]

3. WebGPU Deployment
   - Final format: [.onnx/.bin/etc]
   - Browser loading: [method]
   - Initialization time: X seconds

### Model Size Analysis
| Stage | Size | Download Time (10 Mbps) |
|-------|------|-------------------------|
| Original | 80 MB | 64 seconds |
| ONNX | X MB | Y seconds |
| Optimized | X MB | Y seconds |

### Validation
- How to verify conversion correctness: [method]
- How to test quality: [method]
- Expected quality loss: [%]

### Recommendation
[Feasible/Challenging/Not Viable] with reasoning
```

---

### Section 4: Browser-Side Inference Performance

**Question 4.1: What is expected inference speed?**
- Typical TTS inference time for 1000 words?
- Real-time factor (1.0x = real-time)?
- Comparison: WebGPU vs server-side MLX?
- Impact of model quantization on speed?

**Question 4.2: How does it perform on different devices?**
- Desktop (high-end GPU): X tokens/sec
- Desktop (integrated GPU): X tokens/sec
- Laptop: X tokens/sec
- Mobile (high-end): X tokens/sec
- Mobile (mid-range): X tokens/sec

**Question 4.3: What are the resource requirements?**
- GPU memory needed: X MB
- System RAM needed: X MB
- CPU usage during inference: X%
- Battery impact on mobile devices?

**Question 4.4: What is the user experience?**
- Initial model load time: X seconds
- Subsequent inference: X seconds per paragraph
- Perceived latency vs server-side?
- Progressive enhancement UX?

**Research Methods:**
- Search for WebGPU TTS benchmarks
- Look for similar models (Transformers.js examples)
- Check WebGPU memory limits per browser
- Search for mobile WebGPU performance reports
- Look for real-world WebGPU ML projects

**Expected Output:**
```markdown
## Performance Analysis

### Inference Speed Estimates
| Device Type | GPU | Speed (words/min) | Real-time Factor |
|-------------|-----|-------------------|------------------|
| Desktop High-end | RTX 4090 | X | Xx |
| Desktop Integrated | Intel UHD | X | Xx |
| Laptop | M2 Pro | X | Xx |
| Mobile High-end | A17 Pro | X | Xx |
| Mobile Mid-range | Snapdragon 8 Gen 2 | X | Xx |

### Resource Requirements
- GPU memory: X MB
- System RAM: X MB
- CPU usage: X%
- Battery impact: [assessment for mobile]

### User Experience
- First load: X seconds (model download + init)
- Subsequent use: X seconds per paragraph
- Perceived latency vs server: [comparison]
- Progressive enhancement: [UX flow]

### Bottlenecks
1. [Primary bottleneck]
2. [Secondary bottleneck]
...

### Recommendation
[Acceptable/Marginal/Unacceptable] with reasoning
```

---

### Section 5: Kokoro-Specific Considerations

**Question 5.1: Has anyone converted Kokoro to ONNX/WebGPU?**
- Search GitHub for Kokoro ONNX conversions
- Search for Kokoro browser implementations
- Any published benchmarks?
- Any known issues specific to Kokoro?

**Question 5.2: What is Kokoro's model architecture?**
- What type of model is Kokoro (Transformer, RNN, etc.)?
- What are the key operations?
- Are there any unusual layers?
- How does it compare to other TTS models?

**Question 5.3: What voice data is required?**
- Does Kokoro need voice embeddings?
- How are voices loaded/switched?
- Additional data size beyond model weights?
- Voice switching performance?

**Question 5.4: What are the quality considerations?**
- Quality of PyTorch vs ONNX vs quantized ONNX?
- Acceptable quality loss for web version?
- A/B test requirements?
- User perception of quality differences?

**Research Methods:**
- Search GitHub for "kokoro onnx"
- Search GitHub for "kokoro webgpu"
- Check Kokoro TTS documentation/repo
- Search for similar TTS model conversions
- Check Kokoro model architecture details

**Expected Output:**
```markdown
## Kokoro-Specific Analysis

### Existing Work
- Prior ONNX conversions: [yes/no + links]
- Browser implementations: [yes/no + links]
- Published benchmarks: [yes/no + links]
- Known issues: [list]

### Architecture Compatibility
- Model type: [Transformer/RNN/etc]
- Key operations: [list]
- ONNX compatibility: ✅/⚠️/❌
- Unusual layers: [if any]

### Voice Handling
- Voice embeddings size: X MB per voice
- Total data for 5 voices: X MB
- Voice switching mechanism: [description]
- Loading strategy: [all at once / on-demand]

### Quality Assessment
- Expected quality loss: X%
- User acceptability: [assessment]
- A/B test plan: [if needed]

### Recommendation
[Proceed/Investigate Further/Not Feasible] with reasoning
```

---

### Section 6: Alternative Approaches

**Question 6.1: What are alternatives to WebGPU?**
- **WebNN API**: Status and viability?
- **Transformers.js**: Hugging Face's web inference library?
- **TensorFlow.js**: Compatibility with Kokoro?
- **WebAssembly + SIMD**: CPU-only fallback?

**Question 6.2: What about hybrid approaches?**
- Stream model execution: Process chunks as they download?
- Progressive inference: Show text immediately, audio follows?
- Smart caching: Cache common phrases?
- Partial client-side: Pre-processing only, server does inference?

**Question 6.3: What about fallback strategies?**
- Feature detection: Check for WebGPU support
- Graceful degradation: Fall back to server-side API
- User communication: "Upgrade browser for offline TTS"
- Progressive enhancement: Core features work, WebGPU is bonus

**Research Methods:**
- Research WebNN API status (2025)
- Check Transformers.js capabilities and models
- Look for TensorFlow.js TTS examples
- Search for hybrid TTS approaches
- Review progressive enhancement patterns

**Expected Output:**
```markdown
## Alternative Approaches

### Alternative Technologies
| Technology | Status | Viability | Pros | Cons |
|------------|--------|-----------|------|------|
| WebNN | [status] | [score] | ... | ... |
| Transformers.js | [status] | [score] | ... | ... |
| TensorFlow.js | [status] | [score] | ... | ... |
| WASM + SIMD | [status] | [score] | ... | ... |

### Hybrid Approaches
1. **Streaming Inference**
   - Description: [...]
   - Viability: [...]
   - Implementation: [...]

2. **Progressive Enhancement**
   - Description: [...]
   - Viability: [...]
   - Implementation: [...]

3. [Other approaches]

### Fallback Strategy
```javascript
// Feature detection pattern
if (navigator.gpu) {
  // Use WebGPU TTS
} else {
  // Fall back to server-side API
}
```

### Recommendation
[Recommended approach] with reasoning
```

---

### Section 7: Implementation Complexity & Timeline

**Question 7.1: What is the development effort?**
- Model conversion: X days/weeks
- WebGPU integration: X days/weeks
- Testing and optimization: X days/weeks
- Total estimated effort: X weeks

**Question 7.2: What expertise is required?**
- PyTorch/ONNX export knowledge?
- WebGPU API expertise?
- JavaScript/TypeScript skills?
- ML optimization experience?
- Browser API knowledge?

**Question 7.3: What are the risks?**
- Technical risks: [list]
- Timeline risks: [list]
- Quality risks: [list]
- Browser compatibility risks: [list]

**Question 7.4: What is the maintenance burden?**
- Ongoing browser compatibility testing?
- Model updates/retraining?
- Performance optimization?
- Bug fixing complexity?

**Research Methods:**
- Estimate based on similar projects
- Check complexity of existing WebGPU ML projects
- Review developer experience reports
- Assess documentation quality

**Expected Output:**
```markdown
## Implementation Analysis

### Development Effort
| Phase | Estimated Time | Complexity |
|-------|----------------|------------|
| Model Conversion | X weeks | Low/Medium/High |
| WebGPU Integration | X weeks | Low/Medium/High |
| Testing & Optimization | X weeks | Low/Medium/High |
| Documentation | X weeks | Low/Medium/High |
| **Total** | **X weeks** | **Overall: [rating]** |

### Required Expertise
- [ ] PyTorch/ONNX export (required/nice-to-have)
- [ ] WebGPU API (required/nice-to-have)
- [ ] JavaScript/TypeScript (required/nice-to-have)
- [ ] ML optimization (required/nice-to-have)
- [ ] Browser APIs (required/nice-to-have)

**Team Skill Gap:** [assessment]

### Risk Assessment
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [strategy] |
| [Risk 2] | High/Med/Low | High/Med/Low | [strategy] |
...

### Maintenance Burden
- Browser compatibility testing: [frequency/effort]
- Model updates: [frequency/effort]
- Performance optimization: [ongoing/one-time]
- Bug fixing: [expected complexity]

**Overall Maintenance:** Light/Medium/Heavy

### Recommendation
[Include in MVP / Post-MVP / Skip] with detailed reasoning
```

---

### Section 8: Competitive Analysis

**Question 8.1: Who else is doing browser-based TTS?**
- Google Cloud TTS: Browser implementation?
- Amazon Polly: Client-side options?
- ElevenLabs: Browser SDK?
- Open-source projects: Any browser TTS?

**Question 8.2: What can we learn from them?**
- What technologies do they use?
- What are their performance characteristics?
- What are their limitations?
- How do they handle fallbacks?

**Question 8.3: What is the market expectation?**
- Do users expect client-side TTS?
- Is offline TTS a significant feature?
- What is the privacy value proposition?
- Competitive advantage vs complexity trade-off?

**Research Methods:**
- Research major TTS provider APIs
- Check for browser-based TTS demos
- Search for open-source browser TTS projects
- Review user feedback on existing solutions

**Expected Output:**
```markdown
## Competitive Analysis

### Major Players
| Provider | Browser TTS | Technology | Limitations |
|----------|-------------|------------|-------------|
| Google Cloud TTS | [yes/no] | [tech] | [...] |
| Amazon Polly | [yes/no] | [tech] | [...] |
| ElevenLabs | [yes/no] | [tech] | [...] |
| Mozilla TTS | [yes/no] | [tech] | [...] |

### Key Learnings
1. [Learning 1]
2. [Learning 2]
...

### Market Expectations
- User demand for offline TTS: [assessment]
- Privacy as selling point: [assessment]
- Performance expectations: [assessment]

### Competitive Positioning
**With WebGPU TTS:**
- Unique selling points: [list]
- Competitive advantages: [list]

**Without WebGPU TTS:**
- Impact on product positioning: [assessment]
- Alternative differentiators: [list]

### Recommendation
[Strategic value: High/Medium/Low] with reasoning
```

---

### Section 9: Caching & Storage Strategy

**Question 9.1: How to cache the model?**
- IndexedDB for model storage?
- Cache API for model files?
- Storage quota limits per browser?
- Cache invalidation strategy?

**Question 9.2: What is the storage requirement?**
- Model weights: X MB
- Voice embeddings: X MB per voice
- Total for 5 voices: X MB
- Audio cache (generated): X MB

**Question 9.3: How to handle model updates?**
- Version checking mechanism?
- Automatic updates or user prompt?
- Fallback if update fails?
- Rollback strategy?

**Research Methods:**
- Research IndexedDB best practices
- Check browser storage quotas (2025)
- Look for large file caching examples
- Review service worker caching strategies

**Expected Output:**
```markdown
## Caching & Storage Analysis

### Storage Strategy
- **Method:** IndexedDB / Cache API / [other]
- **Rationale:** [reasoning]

### Storage Requirements
| Item | Size | Priority |
|------|------|----------|
| Kokoro model | X MB | Critical |
| Voice embeddings (×5) | X MB | High |
| Audio cache | X MB | Medium |
| **Total** | **X MB** | |

### Browser Quotas
| Browser | Quota | Sufficient? |
|---------|-------|-------------|
| Chrome | X GB | ✅/❌ |
| Safari | X MB | ✅/❌ |
| Firefox | X GB | ✅/❌ |

### Update Strategy
1. Check model version on app load
2. [Download strategy]
3. [Fallback if update fails]

### Implementation
```javascript
// Pseudocode for caching
async function loadModel() {
  const cached = await checkIndexedDB('kokoro-model');
  if (cached && !isOutdated(cached)) {
    return cached;
  }
  const model = await downloadModel();
  await saveToIndexedDB('kokoro-model', model);
  return model;
}
```

### Recommendation
[Viable/Challenging/Problematic] with reasoning
```

---

### Section 10: User Experience & Progressive Enhancement

**Question 10.1: What is the optimal UX flow?**
- First visit: Model download experience?
- Model loading: Show progress indicator?
- Inference: Show processing state?
- Fallback: Communicate why using server?

**Question 10.2: How to handle the initial download?**
- Auto-download on first use?
- Ask user permission first?
- Show estimated time and size?
- Allow cancellation?

**Question 10.3: What about progressive enhancement?**
- Core features work without WebGPU?
- Enhanced features with WebGPU?
- Clear communication to user?
- Settings to toggle client/server TTS?

**Question 10.4: How to handle errors?**
- Model download fails: [UX]
- Inference fails: [UX]
- Out of memory: [UX]
- Browser not supported: [UX]

**Research Methods:**
- Review PWA download experiences
- Check large ML model web apps
- Review progressive enhancement patterns
- Study error handling best practices

**Expected Output:**
```markdown
## User Experience Analysis

### UX Flow
```
1. User uploads document
2. [WebGPU available?]
   - YES: "Download TTS model for offline use? (80MB, ~60s)"
     - User accepts: Show download progress → Ready
     - User declines: Use server-side TTS
   - NO: Use server-side TTS automatically
3. User clicks Play
4. [Model loaded?]
   - YES: Immediate playback
   - NO: Show "Generating audio..." → Playback
```

### First-Time Download Experience
- **Prompt:** "Download voice model for faster, offline playback?"
- **Details:** 80MB download, ~60 seconds on 10 Mbps
- **Progress:** Visual progress bar with % and time remaining
- **Cancellation:** "Use online TTS instead"

### Progressive Enhancement
| Feature | Without WebGPU | With WebGPU |
|---------|----------------|-------------|
| Text upload | ✅ | ✅ |
| Audio playback | ✅ (server) | ✅ (client) |
| Word highlighting | ✅ | ✅ |
| Voice switching | ✅ (slower) | ✅ (instant) |
| Offline mode | ❌ | ✅ |

### Error Handling
| Error | User Message | Action |
|-------|--------------|--------|
| Download fails | "Couldn't download voice model. Using online TTS." | Fallback to server |
| Inference fails | "Switching to online TTS..." | Fallback to server |
| Out of memory | "Your device doesn't have enough memory. Using online TTS." | Fallback to server |
| Not supported | "Your browser doesn't support offline TTS. Using online TTS." | Fallback to server |

### Settings Panel
```
[x] Enable offline TTS (requires 80MB download)
    [ ] Auto-download on next visit
    [ ] Delete downloaded model (free up space)

Current status: Model loaded, offline mode active
```

### Recommendation
[UX is acceptable / needs refinement / problematic] with reasoning
```

---

## Final Research Report Structure

Your research should produce a comprehensive report with this structure:

```markdown
# WebGPU TTS Research Report
Date: [date]
Researcher: [name]

## Executive Summary
- **Recommendation:** [Include in MVP / Post-MVP / Skip / Need More Info]
- **Confidence Level:** [High / Medium / Low]
- **Key Findings:** [3-5 bullet points]
- **Primary Risks:** [3-5 bullet points]

## 1. Browser Support Analysis
[Section 1 findings]

## 2. ONNX Runtime Web Analysis
[Section 2 findings]

## 3. Model Conversion Analysis
[Section 3 findings]

## 4. Performance Analysis
[Section 4 findings]

## 5. Kokoro-Specific Analysis
[Section 5 findings]

## 6. Alternative Approaches
[Section 6 findings]

## 7. Implementation Analysis
[Section 7 findings]

## 8. Competitive Analysis
[Section 8 findings]

## 9. Caching & Storage Analysis
[Section 9 findings]

## 10. User Experience Analysis
[Section 10 findings]

## 11. Decision Matrix
| Criteria | Weight | Score (1-10) | Weighted Score |
|----------|--------|--------------|----------------|
| Browser Support | 20% | X | X.X |
| Performance | 20% | X | X.X |
| Implementation Complexity | 15% | X | X.X |
| User Experience | 15% | X | X.X |
| Maintenance Burden | 10% | X | X.X |
| Competitive Advantage | 10% | X | X.X |
| Risk Level | 10% | X | X.X |
| **Total** | **100%** | | **X.X / 10** |

**Interpretation:**
- 8.0-10.0: Strong candidate for MVP
- 6.0-7.9: Implement post-MVP
- 4.0-5.9: Defer indefinitely
- 0.0-3.9: Skip

## 12. Recommendation

### Final Recommendation: [Include in MVP / Post-MVP / Skip]

**Rationale:**
[Detailed reasoning based on all research]

**Implementation Plan:** (if recommended)
1. [Step 1]
2. [Step 2]
...

**Fallback Strategy:**
[How to handle if WebGPU fails or is unavailable]

**Success Metrics:**
- [Metric 1]
- [Metric 2]
...

**Go/No-Go Criteria:**
Before committing to implementation:
- [ ] [Criterion 1]
- [ ] [Criterion 2]
...

## 13. Resources & References
- [Link 1]
- [Link 2]
...

## 14. Next Steps
1. [Action item 1]
2. [Action item 2]
...

---

**Report Complete**
```

---

## Research Tools & Resources

### Primary Sources:
- **WebGPU Spec**: https://www.w3.org/TR/webgpu/
- **Can I Use WebGPU**: https://caniuse.com/webgpu
- **MDN WebGPU**: https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API
- **ONNX Runtime Web**: https://onnxruntime.ai/docs/tutorials/web/
- **Transformers.js**: https://huggingface.co/docs/transformers.js

### Search Strategies:
- GitHub: "kokoro tts onnx", "webgpu tts", "onnx runtime web tts"
- Google Scholar: "webgpu machine learning performance"
- Reddit: r/WebGPU, r/MachineLearning, r/webdev
- Hacker News: Search for WebGPU and TTS discussions
- Twitter/X: #WebGPU, #ONNX, #TTS hashtags

### Example Projects to Study:
- Transformers.js demos (Hugging Face)
- ONNX Runtime Web samples
- WebGPU Samples (by browser vendors)
- Web-based ML projects on GitHub

---

## Success Criteria for Research

**Research is COMPLETE when:**
- ✅ All 10 sections have findings
- ✅ Decision matrix is filled out
- ✅ Clear recommendation is made (Include/Post-MVP/Skip)
- ✅ Rationale is well-supported by evidence
- ✅ Implementation plan is detailed (if recommended)
- ✅ Fallback strategy is clear
- ✅ Resources are cited

**Research is HIGH QUALITY when:**
- Evidence is current (2024-2025)
- Multiple sources confirm findings
- Performance numbers are realistic
- Risks are honestly assessed
- Recommendation is actionable
- Report is clear and concise

---

## Important Notes

1. **Be Honest**: If WebGPU TTS is not viable, say so clearly. Don't oversell it.

2. **Be Realistic**: Performance estimates should be conservative, not optimistic.

3. **Cite Sources**: Every claim should have a source (link, documentation, benchmark).

4. **Consider All Angles**: Technical viability is important, but so are UX, complexity, and maintenance.

5. **Think Long-Term**: This is a strategic decision with long-term implications.

6. **Provide Actionable Recommendations**: Don't just say "maybe" - give clear guidance.

---

## Handoff

Once research is complete, provide the final report to the development team. The report should inform:

- **MVP Scope**: Include WebGPU TTS or defer?
- **Architecture**: Server-side only, client-side only, or hybrid?
- **Fallback Strategy**: How to handle browsers without WebGPU?
- **Timeline**: If implementing, how long will it take?

The research report becomes a living document - revisit as browser support evolves.

---

**End of Metaprompt #3**

This metaprompt provides comprehensive research questions and structure for evaluating WebGPU TTS feasibility.
