/* AICC-Lite Frontend Vue 3 App */
const { createApp, ref, computed, onMounted, watch, nextTick } = Vue;

// ============ API client (with offline fallback) ============
const isStandalone = !window.location.hostname.includes('localhost') && window.location.protocol !== 'file:'
    ? false  // Default: assume backend may be available
    : false;

const API_BASE = window.AICC_API_BASE || (
    window.location.port === '8000' ? '' : 'http://127.0.0.1:8000'
);

class ApiClient {
    constructor() {
        this.online = false;
        this.useStandalone = false;
    }

    async health() {
        // 强制 standalone 模式
        if (window.AICC_FORCE_STANDALONE) {
            this.online = false;
            this.useStandalone = true;
            return null;
        }
        try {
            const r = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2000) });
            if (r.ok) {
                this.online = true;
                return await r.json();
            }
        } catch (e) {
            this.online = false;
        }
        return null;
    }

    async _fetch(path, opts = {}) {
        if (!this.online && window.MockBackend) {
            return await window.MockBackend.handle(path, opts);
        }
        const r = await fetch(`${API_BASE}${path}`, {
            headers: { 'Content-Type': 'application/json' },
            ...opts,
        });
        if (!r.ok) throw new Error(`API ${path} failed: ${r.status}`);
        return r.json();
    }

    listConvs() { return this._fetch('/api/v1/conversations'); }
    getConv(id) { return this._fetch(`/api/v1/conversations/${id}`); }
    createConv(data) {
        return this._fetch('/api/v1/conversations', {
            method: 'POST', body: JSON.stringify(data),
        });
    }
    addMessage(convId, payload) {
        return this._fetch(`/api/v1/conversations/${convId}/messages`, {
            method: 'POST', body: JSON.stringify(payload),
        });
    }
    triggerScenario(scenarioId, phone = '13812345678') {
        return this._fetch(`/api/v1/scenarios/${scenarioId}/trigger?phone=${phone}`, { method: 'POST' });
    }
    aiReply(convId) {
        return this._fetch(`/api/v1/conversations/${convId}/ai_reply`, { method: 'POST' });
    }
    handoff(convId, payload) {
        return this._fetch(`/api/v1/conversations/${convId}/handoff`, {
            method: 'POST', body: JSON.stringify(payload),
        });
    }
    resolve(convId) {
        return this._fetch(`/api/v1/conversations/${convId}/resolve`, { method: 'POST' });
    }
    assign(convId, assigneeId = 2) {
        return this._fetch(`/api/v1/conversations/${convId}/assign?assignee_id=${assigneeId}`, { method: 'POST' });
    }
    suggest(convId) {
        return this._fetch(`/api/v1/conversations/${convId}/suggest`, { method: 'POST' });
    }
    translate(text, sourceLang, targetLang) {
        return this._fetch('/api/v1/translate', {
            method: 'POST',
            body: JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang }),
        });
    }
    reset() {
        return this._fetch('/api/v1/demo/reset', { method: 'POST' });
    }
}

const api = new ApiClient();

// ============ WebSocket ============
function connectWebSocket(onEvent) {
    if (!api.online) return null;
    const wsUrl = (API_BASE || `${window.location.protocol}//${window.location.host}`)
        .replace('http://', 'ws://').replace('https://', 'wss://');
    const ws = new WebSocket(`${wsUrl}/ws/agent?token=agent-demo-token`);
    ws.onmessage = (e) => {
        try {
            const msg = JSON.parse(e.data);
            onEvent(msg);
        } catch (err) { /* ignore */ }
    };
    ws.onerror = () => console.warn('WS error');
    ws.onclose = () => {
        console.warn('WS closed, reconnect in 3s');
        setTimeout(() => connectWebSocket(onEvent), 3000);
    };
    return ws;
}

// ============ Vue App ============
const app = createApp({
    setup() {
        const backendOnline = ref(false);
        const conversations = ref([]);
        const currentConvId = ref(null);
        const currentConv = ref(null);
        const scenarioData = ref(null);
        const suggestions = ref([]);
        const aiTyping = ref(false);
        const msgInput = ref('');
        const translateInput = ref('');
        const translateDir = ref('zh-en');
        const translatePlaying = ref(false);
        const toast = ref(null);
        const currentScenario = ref('s1');

        const scenarios = [
            {
                id: 's1', icon: '📡', title: '场景 1: 主动诊断',
                subtitle: '基站负载预测分析',
                description: '客户接通瞬间,系统已并行查到基站异常,主动告知问题、提工单、补偿流量',
                capability: 'Predictive AI',
            },
            {
                id: 's2', icon: '💰', title: '场景 2: 套餐挽留',
                subtitle: 'Behavior-driven LLM',
                description: 'Tool 精确算账,基于忠诚度生成挽留方案,数字 100% 准确',
                capability: 'Behavior-driven LLM',
            },
            {
                id: 's3', icon: '🆘', title: '场景 3: 投诉转人工',
                subtitle: '无缝人机协同',
                description: 'AI 识别投诉情绪,转人工时附完整摘要+建议话术,坐席无缝接管',
                capability: 'Seamless Human-AI',
            },
            {
                id: 's4', icon: '🌐', title: '场景 4: 双向翻译',
                subtitle: 'Translation Bridge',
                description: 'LLM 实时双向翻译,1 个座席服务多语种,商务对话自然流畅',
                capability: 'Translation Bridge',
            },
        ];

        // ============ Helpers ============
        const showToast = (text, type = 'info') => {
            toast.value = { text, type };
            setTimeout(() => { toast.value = null; }, 3000);
        };
        const statusLabel = (s) => ({
            pending: '待处理', open: '处理中', resolved: '已结束', snoozed: '已暂停',
        }[s] || s);
        const scenarioTitle = (sid) => scenarios.find(s => s.id === sid)?.title || sid;
        const tierLabel = (t) => ({
            loyal_3yr: '🌟 3年老客户', vip: 'VIP', regular: '普通',
        }[t] || t);
        const planLabel = (p) => ({
            '199_basic': '199基础版', '299_standard': '299标准版', '399_premium': '399尊享版',
        }[p] || p);
        const toolLabel = (t) => ({
            create_ticket: '创建工单', grant_voucher: '发放流量包',
            apply_retention_offer: '激活优惠', calculate_actual_cost: '精确算账',
        }[t] || t);
        const formatTime = (iso) => {
            if (!iso) return '';
            const d = new Date(iso);
            return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        };
        const senderName = (m) => {
            if (m.sender_type === 'Contact') return currentConv.value?.contact?.name || '客户';
            if (m.sender_type === 'AgentBot') return '🤖 AI 助手';
            if (m.sender_type === 'Captain') return '🦸 Captain AI';
            return '客服';
        };
        const msgClass = (m) => {
            if (m.message_type === 2) return 'row-activity';
            if (m.sender_type === 'Contact') return 'row-customer';
            if (m.sender_type === 'AgentBot' || m.sender_type === 'Captain') return 'row-bot';
            return 'row-agent';
        };
        const bubbleClass = (m) => {
            if (m.sender_type === 'Contact') return 'bubble-customer';
            if (m.sender_type === 'AgentBot') return 'bubble-ai';
            if (m.sender_type === 'Captain') return 'bubble-captain';
            return 'bubble-agent';
        };

        const scenarioInsightTitle = () => {
            const titles = {
                s1: '📡 实时网络诊断',
                s2: '💰 用量与挽留分析',
                s3: '🆘 投诉上下文',
                s4: '🌐 翻译桥接信息',
            };
            return titles[currentConv.value?.scenario_id] || 'AI 分析';
        };

        // ============ Backend health check ============
        const checkBackend = async () => {
            const h = await api.health();
            backendOnline.value = !!h;
            if (h) {
                showToast(`已连接后端 v${h.version} (LLM: ${h.llm_enabled ? '已启用' : '兜底模式'})`, 'success');
            } else {
                showToast('未连接后端,使用前端 Mock 模式', 'warn');
            }
        };

        // ============ Conversations ============
        const loadConvs = async () => {
            try {
                const r = await api.listConvs();
                conversations.value = r.data || [];
            } catch (e) {
                console.error('Load convs failed:', e);
            }
        };

        const loadConv = async (id) => {
            try {
                const r = await api.getConv(id);
                currentConv.value = r;
                await nextTick();
                scrollToBottom();
            } catch (e) {
                console.error('Load conv failed:', e);
            }
        };

        const selectConv = async (id) => {
            currentConvId.value = id;
            await loadConv(id);
            await loadCaptainSuggest();
        };

        const switchScenario = (sid) => {
            currentScenario.value = sid;
        };

        const startScenario = async () => {
            try {
                const r = await api.triggerScenario(currentScenario.value);
                scenarioData.value = r.data;
                await loadConvs();
                await selectConv(r.conversation_id);
                showToast(`已触发场景 ${currentScenario.value.toUpperCase()}`, 'success');
                // 自动播放 AI 第一句
                setTimeout(() => {
                    autoPlayScenarioFlow(r);
                }, 500);
            } catch (e) {
                showToast('触发场景失败: ' + e.message, 'error');
            }
        };

        const autoPlayScenarioFlow = async (triggerResp) => {
            const data = triggerResp.data;
            const convId = triggerResp.conversation_id;

            if (data.scenario === 's1' && data.ai_proactive_message) {
                // S1: 自动播放 AI 主动消息
                aiTyping.value = true;
                await new Promise(r => setTimeout(r, 800));
                aiTyping.value = false;
                await api.addMessage(convId, {
                    content: data.ai_proactive_message,
                    sender_type: 'AgentBot', sender_id: 1,
                    content_attributes: { source: 'predictive_ai', tools_called: data.actions?.map(a => a.tool) },
                });
                await loadConv(convId);
                await loadCaptainSuggest();

                // 接续:工单已创建
                setTimeout(async () => {
                    aiTyping.value = true;
                    await new Promise(r => setTimeout(r, 1200));
                    aiTyping.value = false;
                    const ticket = data.actions?.find(a => a.tool === 'create_ticket')?.result;
                    const voucher = data.actions?.find(a => a.tool === 'grant_voucher')?.result;
                    const followup = `我已为您提交基站优化工单,工单号 ${ticket?.ticket_id || 'WO-DEMO-001'},预计30分钟内恢复。同时为您发放 ${voucher?.data_gb || 10}G 免费流量包作为补偿,请查收短信确认。`;
                    await api.addMessage(convId, {
                        content: followup,
                        sender_type: 'AgentBot', sender_id: 1,
                        content_attributes: { source: 'follow_up' },
                    });
                    await loadConv(convId);
                }, 2500);
            } else if (data.scenario === 's2') {
                aiTyping.value = true;
                await new Promise(r => setTimeout(r, 800));
                aiTyping.value = false;
                await api.addMessage(convId, {
                    content: '您好张先生,有什么可以帮您?',
                    sender_type: 'AgentBot', sender_id: 1,
                });
                await loadConv(convId);
            } else if (data.scenario === 's3') {
                aiTyping.value = true;
                await new Promise(r => setTimeout(r, 800));
                aiTyping.value = false;
                await api.addMessage(convId, {
                    content: '您好张先生,有什么可以帮您?',
                    sender_type: 'AgentBot', sender_id: 1,
                });
                await loadConv(convId);
            } else if (data.scenario === 's4') {
                aiTyping.value = true;
                await new Promise(r => setTimeout(r, 800));
                aiTyping.value = false;
                await api.addMessage(convId, {
                    content: `已为您接通 ${data.callee?.name},通话将自动双向翻译,请稍候`,
                    sender_type: 'AgentBot', sender_id: 1,
                });
                await loadConv(convId);
            }
        };

        const sendCustomerMsg = async () => {
            if (!msgInput.value || !currentConvId.value || aiTyping.value) return;
            const text = msgInput.value.trim();
            msgInput.value = '';
            try {
                await api.addMessage(currentConvId.value, {
                    content: text,
                    sender_type: 'Contact', sender_id: 1,
                });
                await loadConv(currentConvId.value);

                // 自动 AI 回复(除非 S4 翻译模式)
                if (currentConv.value?.scenario_id !== 's4') {
                    setTimeout(() => generateAIReply(text), 600);
                }
            } catch (e) {
                showToast('发送失败: ' + e.message, 'error');
            }
        };

        const generateAIReply = async (lastUserMsg = '') => {
            if (!currentConvId.value || aiTyping.value) return;
            aiTyping.value = true;

            // S3 检测投诉关键词,自动触发 handoff
            if (currentConv.value?.scenario_id === 's3' &&
                /投诉|不满|没解决|没用|垃圾|气|生气|不爽/.test(lastUserMsg)) {
                aiTyping.value = false;
                await new Promise(r => setTimeout(r, 800));
                await triggerHandoff();
                return;
            }

            try {
                const r = await api.aiReply(currentConvId.value);
                await loadConv(currentConvId.value);
                await loadCaptainSuggest();
            } catch (e) {
                showToast('AI 回复失败: ' + e.message, 'error');
            } finally {
                aiTyping.value = false;
            }
        };

        const triggerHandoff = async () => {
            if (!currentConvId.value) return;
            try {
                aiTyping.value = true;
                await new Promise(r => setTimeout(r, 600));
                aiTyping.value = false;
                await api.addMessage(currentConvId.value, {
                    content: '非常抱歉给您带来困扰,我马上为您转接专属客服,请稍候。',
                    sender_type: 'AgentBot', sender_id: 1,
                });
                await api.handoff(currentConvId.value, {
                    reason: 'complaint',
                    sentiment_score: 2,
                    ai_summary: '客户因之前 WO-20260601-077 工单未解决而投诉,情绪激动。建议:先共情致歉,确认问题,提供升级方案+补偿。',
                });
                await loadConv(currentConvId.value);
                await loadConvs();
                showToast('已转人工坐席,完整上下文已传递', 'success');
            } catch (e) {
                showToast('转接失败: ' + e.message, 'error');
            }
        };

        const acceptCall = async () => {
            if (!currentConvId.value) return;
            try {
                await api.assign(currentConvId.value, 2);
                await loadConv(currentConvId.value);
                await loadConvs();
                await api.addMessage(currentConvId.value, {
                    content: '客服小李已接听,正在为您服务',
                    sender_type: 'User', sender_id: 2,
                    content_attributes: { activity: 'agent_joined' },
                });
                await loadConv(currentConvId.value);
                showToast('已接听通话', 'success');
            } catch (e) {
                showToast('接听失败: ' + e.message, 'error');
            }
        };

        const resolve = async () => {
            if (!currentConvId.value) return;
            try {
                await api.resolve(currentConvId.value);
                await loadConv(currentConvId.value);
                await loadConvs();
                showToast('会话已结束', 'success');
            } catch (e) {
                showToast('结束失败: ' + e.message, 'error');
            }
        };

        const loadCaptainSuggest = async () => {
            if (!currentConvId.value) return;
            try {
                const r = await api.suggest(currentConvId.value);
                suggestions.value = r.suggestions || [];
            } catch (e) {
                suggestions.value = [];
            }
        };

        const useSuggestion = (text) => {
            msgInput.value = text;
            showToast('已填入输入框,请点击发送', 'info');
        };

        const triggerVoiceInput = () => {
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {
                showToast('当前浏览器不支持语音输入', 'warn');
                return;
            }
            const rec = new SR();
            rec.lang = 'zh-CN';
            rec.continuous = false;
            rec.onresult = (e) => {
                msgInput.value = e.results[0][0].transcript;
            };
            rec.onerror = (e) => showToast('语音错误: ' + e.error, 'error');
            rec.start();
            showToast('正在聆听... 请说话', 'info');
        };

        // ============ S4 Translation ============
        const playTranslateDialog = async (startIdx = 0) => {
            if (!currentConvId.value || translatePlaying.value) return;
            translatePlaying.value = true;

            const dialog = scenarioData.value?.preset_dialog || [];
            for (let i = startIdx; i < dialog.length; i++) {
                const entry = dialog[i];
                const isZhSpeaker = entry.speaker === 'user_zh';
                const sourceText = isZhSpeaker ? entry.zh : entry.en;
                const targetText = isZhSpeaker ? entry.en : entry.zh;

                // 添加 source 消息
                await api.addMessage(currentConvId.value, {
                    content: sourceText,
                    sender_type: isZhSpeaker ? 'Contact' : 'AgentBot',
                    sender_id: 1,
                    content_attributes: {
                        translation: 'source',
                        lang: isZhSpeaker ? 'zh' : 'en',
                        speaker: entry.speaker,
                    },
                });
                await loadConv(currentConvId.value);

                // 模拟翻译延迟
                await new Promise(r => setTimeout(r, 1000));

                // 添加翻译结果
                await api.addMessage(currentConvId.value, {
                    content: `[翻译] ${targetText}`,
                    sender_type: 'Captain',
                    sender_id: 0,
                    content_attributes: {
                        translation: 'translated',
                        from_lang: isZhSpeaker ? 'zh' : 'en',
                        to_lang: isZhSpeaker ? 'en' : 'zh',
                    },
                });
                await loadConv(currentConvId.value);

                await new Promise(r => setTimeout(r, 1500));
            }

            translatePlaying.value = false;
            showToast('对话翻译完成', 'success');
        };

        const customTranslate = async () => {
            if (!translateInput.value || !currentConvId.value) return;
            const text = translateInput.value.trim();
            const [src, tgt] = translateDir.value.split('-');
            try {
                await api.addMessage(currentConvId.value, {
                    content: text,
                    sender_type: 'Contact',
                    sender_id: 1,
                    content_attributes: { translation: 'source', lang: src },
                });
                await loadConv(currentConvId.value);

                const r = await api.translate(text, src, tgt);
                await api.addMessage(currentConvId.value, {
                    content: `[翻译 ${src}→${tgt}] ${r.target}`,
                    sender_type: 'Captain',
                    sender_id: 0,
                    content_attributes: { translation: 'translated', from_lang: src, to_lang: tgt, latency_ms: r.latency_ms },
                });
                await loadConv(currentConvId.value);
                translateInput.value = '';
            } catch (e) {
                showToast('翻译失败: ' + e.message, 'error');
            }
        };

        const resetDemo = async () => {
            if (!confirm('确定清空所有会话吗?')) return;
            try {
                await api.reset();
                conversations.value = [];
                currentConvId.value = null;
                currentConv.value = null;
                scenarioData.value = null;
                suggestions.value = [];
                showToast('Demo 已重置', 'success');
            } catch (e) {
                showToast('重置失败: ' + e.message, 'error');
            }
        };

        const scrollToBottom = () => {
            const list = document.querySelector('.messages');
            if (list) list.scrollTop = list.scrollHeight;
        };

        // Watch messages length to autoscroll
        watch(() => currentConv.value?.messages?.length, () => {
            nextTick(scrollToBottom);
        });

        // ============ Mount ============
        onMounted(async () => {
            await checkBackend();
            if (api.online) {
                await loadConvs();
                connectWebSocket((msg) => {
                    if (msg.event === 'message.created' && currentConvId.value === msg.data.conversation_id) {
                        loadConv(currentConvId.value);
                    }
                    if (msg.event === 'conversation.created' || msg.event === 'conversation.handoff') {
                        loadConvs();
                    }
                });
            } else {
                // 前端 standalone 模式 - 由 mock-backend.js 处理
                if (window.MockBackend) {
                    api.online = true; // 视作 online
                    api.useStandalone = true;
                    await loadConvs();
                }
            }
        });

        return {
            backendOnline, conversations, currentConvId, currentConv,
            scenarioData, suggestions, aiTyping,
            msgInput, translateInput, translateDir, translatePlaying,
            toast, currentScenario, scenarios,
            statusLabel, scenarioTitle, tierLabel, planLabel, toolLabel,
            formatTime, senderName, msgClass, bubbleClass, scenarioInsightTitle,
            switchScenario, selectConv, startScenario,
            sendCustomerMsg, generateAIReply, triggerHandoff,
            acceptCall, resolve, loadCaptainSuggest, useSuggestion,
            triggerVoiceInput, playTranslateDialog, customTranslate, resetDemo,
        };
    }
});

app.mount('#app');
