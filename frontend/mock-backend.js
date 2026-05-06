/* Mock Backend - 让前端在没有真实后端时也能完整演示 4 大场景
   用于 GitHub Pages 等纯静态托管 */

(function () {
    const STORE_KEY = 'aicc_lite_store_v1';

    // ============ Mock Data ============
    const MOCK_CONTACT = {
        id: 1, name: '张先生', phone: '13812345678', email: 'zhang@example.com',
        custom_attributes: {
            tier: 'loyal_3yr', current_plan: '399_premium',
            registration_date: '2023-03-15', preferred_language: 'zh',
            tags: ['VIP客户', '3年老客户', '高活跃'],
        },
    };

    const S1_DIAGNOSIS = {
        phone: '13812345678', base_station: 'BS-008-朝阳区',
        load_percent: 87, signal_strength_dbm: -98,
        issue_type: 'cell_congestion', fix_eta_minutes: 30,
        neighboring_users_affected: 234,
        compensation: { data_voucher_mb: 10240, voucher_id: 'VCH-S1-DEMO-001' },
        ai_proactive_message: '我注意到您所在区域基站当前负载偏高,您是不是觉得网速有点慢?',
    };

    const S2_USAGE = {
        phone: '13812345678', monthly_data_gb: 68, monthly_voice_minutes: 480,
        device_count: 4, top_apps: ['腾讯会议', '微信视频', 'B站', '网易云'],
        peak_hours: ['09:00-12:00', '20:00-23:00'],
    };

    const S2_OFFERS = [
        {
            id: 'loyal_3yr_v1', name: '老客户专属优惠', discount: 0.9,
            new_monthly_cost: 359, savings_per_month: 40,
            bonus: '家庭宽带提速 500M / 持续 6 个月',
            valid_for_months: 12, eligibility: '3年以上忠诚客户',
        },
        {
            id: 'data_pack_addon', name: '流量加油包', discount: 1.0,
            new_monthly_cost: 399, savings_per_month: 0,
            bonus: '额外赠送 50G 国内流量 / 月',
            valid_for_months: 6, eligibility: '所有用户',
        },
    ];

    const PLANS = {
        '199_basic': {
            id: '199_basic', name: '199 基础版', base: 199,
            data_quota_gb: 30, data_overage_per_gb: 3,
            voice_quota_min: 300, voice_overage_per_min: 0.15,
        },
        '299_standard': {
            id: '299_standard', name: '299 标准版', base: 299,
            data_quota_gb: 60, data_overage_per_gb: 2,
            voice_quota_min: 600, voice_overage_per_min: 0.1,
        },
        '399_premium': {
            id: '399_premium', name: '399 尊享版(当前)', base: 399,
            data_quota_gb: 100, data_overage_per_gb: 0,
            voice_quota_min: 1000, voice_overage_per_min: 0,
        },
    };

    const S3_COMPLAINT = {
        phone: '13812345678',
        previous_complaints: [{
            ticket_id: 'WO-20260601-077', issue: '网速持续慢,影响家人在线学习',
            status: 'supposedly_resolved', actual_resolved: false, created_at: '2026-04-25',
        }],
        ai_handoff_summary: '客户因之前 WO-20260601-077 工单未解决而投诉,情绪激动,建议优先处理并提供升级方案',
        suggested_agent_response_template: [
            "1. 先共情:'非常抱歉给您带来困扰'",
            "2. 致歉:'之前的处理没有彻底解决问题'",
            "3. 确认:'让我详细了解一下当前情况'",
            "4. 提供方案:'我会为您升级处理,优先调度技术团队'",
        ],
        sentiment_score: 2, urgency_level: 'high',
    };

    const S4_TRANSLATION = {
        phone: '13812345678',
        callee: {
            name: 'Ahmed Al-Rashid', phone: '+966-50-1234567', language: 'en',
            company: 'Saudi Logistics Co.', country: 'Saudi Arabia',
        },
        context: '上次合同付款条款讨论',
        preset_dialog: [
            { speaker: 'user_zh', zh: '你好 Ahmed,关于上次合同的付款条款,我们这边的财务说需要分两期支付。',
              en: 'Hi Ahmed, regarding the payment terms from last contract, our finance department says we need to pay in two installments.' },
            { speaker: 'ahmed_en', en: "Hi, that's fine. The first installment can be made next Monday, and the second installment within 30 days.",
              zh: '你好,这个安排可以。第一期款项可以下周一支付,第二期款项 30 天内完成。' },
            { speaker: 'user_zh', zh: '好的,谢谢 Ahmed,稍后给您发邮件确认细节。',
              en: "Great, thank you Ahmed. I'll send you an email shortly to confirm the details." },
            { speaker: 'ahmed_en', en: "You're welcome, looking forward to it.",
              zh: '不客气,期待您的邮件。' },
        ],
    };

    // ============ Storage ============
    function loadStore() {
        try {
            const raw = localStorage.getItem(STORE_KEY);
            if (raw) return JSON.parse(raw);
        } catch {}
        return { conversations: [], messages: [], next_conv_id: 1, next_msg_id: 1 };
    }

    function saveStore(s) {
        try { localStorage.setItem(STORE_KEY, JSON.stringify(s)); } catch {}
    }

    // ============ Logic helpers ============
    function calculate_actual_cost(plan, monthly_data_gb, monthly_voice_min) {
        const rate = PLANS[plan];
        if (!rate) return { error: 'Unknown plan' };
        const data_overage = Math.max(0, monthly_data_gb - rate.data_quota_gb);
        const data_overage_cost = data_overage * rate.data_overage_per_gb;
        const voice_overage = Math.max(0, monthly_voice_min - rate.voice_quota_min);
        const voice_overage_cost = voice_overage * rate.voice_overage_per_min;
        const total = rate.base + data_overage_cost + voice_overage_cost;
        const current_total = 399;
        return {
            plan, plan_name: rate.name, base_cost: rate.base,
            data_quota_gb: rate.data_quota_gb, data_used_gb: monthly_data_gb,
            data_overage_gb: Math.round(data_overage * 10) / 10,
            data_overage_per_gb: rate.data_overage_per_gb,
            data_overage_cost: Math.round(data_overage_cost * 100) / 100,
            voice_quota_min: rate.voice_quota_min, voice_used_min: monthly_voice_min,
            voice_overage_min: voice_overage, voice_overage_per_min: rate.voice_overage_per_min,
            voice_overage_cost: Math.round(voice_overage_cost * 100) / 100,
            total: Math.round(total * 100) / 100,
            vs_current: Math.round((total - current_total) * 100) / 100,
            recommendation: total < current_total ? 'save' : 'more_expensive',
        };
    }

    function fakeId() {
        return `WO-DEMO-${Math.floor(Math.random() * 999).toString().padStart(3, '0')}`;
    }

    function nowIso() { return new Date().toISOString(); }

    // ============ Fallback chat (no LLM) ============
    function fallbackReply(scenarioId, lastMsg = '', conv) {
        const responses = {
            s1: [
                '您好张先生,我已经为您处理了基站优化工单',
                '工单号 WO-20260605-001,预计30分钟内恢复',
                '为补偿您,我们额外赠送 10G 免费流量包,请查收短信确认',
            ],
            s2_降套餐: '张先生,我帮您算一下:您每月平均流量68G,通话480分钟。如果降到199套餐,流量超出按¥3/GB计费大约¥114,通话超出按¥0.15/分钟大约¥27,加上套餐费¥199,实际花费会到¥340左右,反而比当前贵¥-59。',
            s2_老客户: '作为您 3 年老客户,我可以为您申请专属优惠:保留 399 套餐核心权益,享受 9 折 ¥359/月,同时赠送家庭宽带提速到 500M,持续 6 个月。您看可以吗?',
            s2_default: '您好张先生,有什么可以帮您?',
            s3_default: '非常抱歉给您带来困扰,我马上为您升级处理,优先调度技术团队。',
            s4_default: 'Translation in progress...',
        };

        if (scenarioId === 's2') {
            if (/降|便宜|低|199/.test(lastMsg)) return responses.s2_降套餐;
            if (/办法|优惠|那|怎么/.test(lastMsg)) return responses.s2_老客户;
            return responses.s2_default;
        }
        if (scenarioId === 's3') return responses.s3_default;
        if (scenarioId === 's1') return '您好张先生,有什么可以帮您?';
        return '您好张先生,有什么可以帮您?';
    }

    // ============ Mock API handlers ============
    const handlers = {
        '/api/health': (method, body) => {
            return { status: 'ok', service: 'AICC-Lite (Standalone Mock)', version: '3.0.0', llm_enabled: false, timestamp: nowIso() };
        },

        '/api/v1/conversations': (method, body) => {
            const store = loadStore();
            if (method === 'GET') {
                return {
                    data: store.conversations.map(c => ({
                        ...c,
                        contact: MOCK_CONTACT,
                        messages_count: store.messages.filter(m => m.conversation_id === c.id).length,
                        last_message: (store.messages.filter(m => m.conversation_id === c.id).slice(-1)[0] || {}).content || null,
                    })),
                    total: store.conversations.length,
                };
            }
            if (method === 'POST') {
                const conv = {
                    id: store.next_conv_id++,
                    account_id: 1, inbox_id: body?.inbox_id || 1, contact_id: 1,
                    assignee_id: null, status: 'pending',
                    scenario_id: body?.scenario_id || null,
                    additional_attributes: { channel: 'voice' },
                    created_at: nowIso(), updated_at: nowIso(),
                };
                store.conversations.push(conv);
                saveStore(store);
                return { id: conv.id, status: conv.status, scenario_id: conv.scenario_id };
            }
        },

        '/api/v1/demo/reset': (method) => {
            if (method === 'POST') {
                saveStore({ conversations: [], messages: [], next_conv_id: 1, next_msg_id: 1 });
                return { status: 'reset' };
            }
        },

        '/api/v1/translate': (method, body) => {
            // 查预设对话
            for (const entry of S4_TRANSLATION.preset_dialog) {
                if (body.source_lang === 'zh' && (entry.zh || '').trim() === body.text.trim()) {
                    return { source: body.text, target: entry.en, source_lang: 'zh', target_lang: 'en', method: 'preset', latency_ms: 50 };
                }
                if (body.source_lang === 'en' && (entry.en || '').trim() === body.text.trim()) {
                    return { source: body.text, target: entry.zh, source_lang: 'en', target_lang: 'zh', method: 'preset', latency_ms: 50 };
                }
            }
            // Fallback: 简单标记
            const fakeTrans = body.source_lang === 'zh'
                ? `[Translation] ${body.text}`
                : `[翻译] ${body.text}`;
            return { source: body.text, target: fakeTrans, source_lang: body.source_lang, target_lang: body.target_lang, method: 'fallback', latency_ms: 200 };
        },
    };

    // 动态路由(包含路径参数)
    function routeRequest(path, method, body) {
        const store = loadStore();

        // /api/v1/conversations/{id}
        let m = path.match(/^\/api\/v1\/conversations\/(\d+)$/);
        if (m) {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) throw new Error('Conversation not found');
            const messages = store.messages.filter(x => x.conversation_id === id);
            return {
                ...conv,
                contact: MOCK_CONTACT,
                messages,
            };
        }

        // /api/v1/conversations/{id}/messages
        m = path.match(/^\/api\/v1\/conversations\/(\d+)\/messages$/);
        if (m && method === 'POST') {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) throw new Error('Conversation not found');
            const msg = {
                id: store.next_msg_id++,
                conversation_id: id,
                content: body.content,
                sender_type: body.sender_type || 'Contact',
                sender_id: body.sender_id || 1,
                message_type: body.sender_type === 'Contact' ? 0 : (body.content_attributes?.activity ? 2 : 1),
                content_attributes: body.content_attributes || {},
                created_at: nowIso(),
            };
            store.messages.push(msg);
            conv.updated_at = nowIso();
            saveStore(store);
            return msg;
        }

        // /api/v1/conversations/{id}/handoff
        m = path.match(/^\/api\/v1\/conversations\/(\d+)\/handoff$/);
        if (m && method === 'POST') {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) throw new Error('Conversation not found');
            conv.status = 'open';
            // 添加 summary 消息
            const sumMsg = {
                id: store.next_msg_id++,
                conversation_id: id,
                content: `🤖 AI 转人工分析:\n原因: ${body.reason}\n情绪评分: ${body.sentiment_score}/10\n摘要: ${body.ai_summary || '无'}`,
                sender_type: 'Captain', sender_id: 0, message_type: 1,
                content_attributes: { type: 'ai_handoff_summary', data: body },
                created_at: nowIso(),
            };
            store.messages.push(sumMsg);
            saveStore(store);
            return { id: conv.id, status: conv.status };
        }

        // /api/v1/conversations/{id}/resolve
        m = path.match(/^\/api\/v1\/conversations\/(\d+)\/resolve$/);
        if (m && method === 'POST') {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) throw new Error('Conversation not found');
            conv.status = 'resolved';
            saveStore(store);
            return { id: conv.id, status: conv.status };
        }

        // /api/v1/conversations/{id}/assign
        m = path.match(/^\/api\/v1\/conversations\/(\d+)\/assign/);
        if (m && method === 'POST') {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) throw new Error('Conversation not found');
            conv.assignee_id = 2;
            if (conv.status === 'pending') conv.status = 'open';
            saveStore(store);
            return { id: conv.id, status: conv.status, assignee_id: 2 };
        }

        // /api/v1/conversations/{id}/ai_reply
        m = path.match(/^\/api\/v1\/conversations\/(\d+)\/ai_reply$/);
        if (m && method === 'POST') {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) throw new Error('Conversation not found');
            const lastUserMsg = store.messages.filter(x => x.conversation_id === id && x.sender_type === 'Contact').slice(-1)[0];
            const reply = fallbackReply(conv.scenario_id, lastUserMsg?.content || '', conv);
            const msg = {
                id: store.next_msg_id++,
                conversation_id: id,
                content: reply,
                sender_type: 'AgentBot', sender_id: 1, message_type: 1,
                content_attributes: { source: 'mock_ai' },
                created_at: nowIso(),
            };
            store.messages.push(msg);
            saveStore(store);
            return { message_id: msg.id, content: reply, tool_calls: [] };
        }

        // /api/v1/conversations/{id}/suggest
        m = path.match(/^\/api\/v1\/conversations\/(\d+)\/suggest$/);
        if (m && method === 'POST') {
            const id = parseInt(m[1]);
            const conv = store.conversations.find(c => c.id === id);
            if (!conv) return { suggestions: [], captain_summary: '' };
            const suggestions = {
                s1: [
                    '您好张先生,我已经为您处理了基站优化工单',
                    '工单号 WO-20260605-001,预计30分钟内恢复',
                    '为补偿您,我们额外赠送 10G 免费流量包',
                ],
                s2: [
                    '考虑您的实际使用,降套餐反而会多花钱',
                    '作为3年老客户,可享专属9折优惠 359元/月',
                    '同时赠送家庭宽带提速 500M,持续6个月',
                ],
                s3: [
                    '非常抱歉给您带来困扰,我会优先处理',
                    '我先共情客户情绪,然后确认问题细节',
                    '提供升级方案+补偿,确保客户满意',
                ],
                s4: [
                    '翻译质量稳定,延迟<800ms',
                    '保留商务对话礼貌语气',
                    '已记录关键决策点供后续跟进',
                ],
            };
            return { conversation_id: id, scenario_id: conv.scenario_id, suggestions: suggestions[conv.scenario_id] || [], captain_summary: '' };
        }

        // /api/v1/scenarios/{sid}/trigger
        m = path.match(/^\/api\/v1\/scenarios\/(s\d)\/trigger/);
        if (m && method === 'POST') {
            const sid = m[1];
            const conv = {
                id: store.next_conv_id++,
                account_id: 1, inbox_id: 1, contact_id: 1,
                assignee_id: null, status: 'pending', scenario_id: sid,
                additional_attributes: { channel: 'voice' },
                created_at: nowIso(), updated_at: nowIso(),
            };
            store.conversations.push(conv);

            // activity msg
            const activityMsg = {
                id: store.next_msg_id++,
                conversation_id: conv.id,
                content: `📞 来电接通 - 场景: ${sid.toUpperCase()} - 客户: 张先生 (13812345678)`,
                sender_type: 'User', sender_id: 1, message_type: 2,
                content_attributes: { activity: 'call_started', scenario: sid },
                created_at: nowIso(),
            };
            store.messages.push(activityMsg);
            saveStore(store);

            let data;
            if (sid === 's1') {
                data = {
                    scenario: 's1', phase: 'predictive_analysis',
                    contact: MOCK_CONTACT, diagnosis: S1_DIAGNOSIS,
                    ai_proactive_message: `您好${MOCK_CONTACT.name},感谢致电。${S1_DIAGNOSIS.ai_proactive_message}`,
                    actions: [
                        { tool: 'create_ticket', result: { success: true, ticket_id: 'WO-20260605-001', phone: '13812345678', issue_type: 'slow_network', priority: 'high', estimated_resolution_minutes: 30, assigned_team: '网络优化组' } },
                        { tool: 'grant_voucher', result: { success: true, voucher_id: 'VCH-DEMO-001', phone: '13812345678', data_mb: 10240, data_gb: 10, message: '已为您发放 10G 免费流量包,有效期 30 天' } },
                    ],
                };
            } else if (sid === 's2') {
                data = {
                    scenario: 's2', phase: 'retention_analysis',
                    contact: MOCK_CONTACT, usage: S2_USAGE, offers: S2_OFFERS,
                    cost_analysis: calculate_actual_cost('199_basic', S2_USAGE.monthly_data_gb, S2_USAGE.monthly_voice_minutes),
                    ai_argument: '如果降到199套餐,实际月费会到¥340,反而比当前贵¥-59。建议保留399套餐,享受老客户9折优惠359元/月。',
                };
            } else if (sid === 's3') {
                data = {
                    scenario: 's3', phase: 'handoff',
                    contact: MOCK_CONTACT, complaint_context: S3_COMPLAINT,
                    handoff: {
                        reason: 'complaint', sentiment_score: 2,
                        ai_summary: S3_COMPLAINT.ai_handoff_summary,
                        suggested_response: S3_COMPLAINT.suggested_agent_response_template,
                        urgency: S3_COMPLAINT.urgency_level,
                    },
                };
            } else {
                data = {
                    scenario: 's4', phase: 'translation_bridge',
                    contact: MOCK_CONTACT, callee: S4_TRANSLATION.callee,
                    context: S4_TRANSLATION.context, preset_dialog: S4_TRANSLATION.preset_dialog,
                };
            }
            return { conversation_id: conv.id, scenario_id: sid, data };
        }

        return null;
    }

    // ============ Public API ============
    window.MockBackend = {
        async handle(path, opts = {}) {
            const method = opts.method || 'GET';
            let body = null;
            if (opts.body) {
                try { body = JSON.parse(opts.body); } catch { body = opts.body; }
            }

            // 模拟网络延迟
            await new Promise(r => setTimeout(r, 100 + Math.random() * 200));

            // 静态路径
            // 取路径部分(去掉 query string)
            const pathOnly = path.split('?')[0];

            const handler = handlers[pathOnly];
            if (handler) {
                const result = handler(method, body);
                if (result !== undefined) return result;
            }

            // 动态路由
            const result = routeRequest(pathOnly, method, body);
            if (result !== null && result !== undefined) return result;

            console.warn('Mock backend: unhandled', method, path);
            return {};
        },
    };

    console.log('🎭 AICC-Lite Mock Backend loaded (standalone mode)');
})();
