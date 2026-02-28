<template>
	<view class="chat-page">
		<!-- 自定义顶部导航栏 -->
		<view class="custom-navbar">
			<view class="navbar-content">
				<view class="navbar-left">
					<text class="app-logo">🤖</text>
					<text class="app-title">AI小伙伴</text>
				</view>
				<view class="navbar-right">
					<text class="status-text">{{ isProcessing ? '思考中...' : '在线' }}</text>
				</view>
			</view>
		</view>

		<!-- AI头像区域 -->
		<view class="ai-section">
			<view class="ai-avatar-wrapper">
				<view class="ai-avatar" :class="avatarAnimation">
					<text class="ai-emoji">{{ aiEmoji }}</text>
				</view>
				<view class="ai-status-dot" :class="statusClass"></view>
			</view>
			<view class="ai-bubble" v-if="aiStatus">
				<text>{{ aiStatus }}</text>
			</view>
		</view>

		<!-- 对话历史 -->
		<scroll-view 
			class="chat-history" 
			scroll-y 
			:scroll-into-view="scrollToId"
			v-if="messages.length > 0"
		>
			<view 
				class="message-item" 
				v-for="(msg, index) in messages" 
				:key="index"
				:id="'msg-' + index"
				:class="msg.type"
			>
				<view class="message-avatar">
					<text>{{ msg.type === 'user' ? '👧' : '🤖' }}</text>
				</view>
				<view class="message-content">
					<view class="message-bubble">
						<text class="message-text">{{ msg.text }}</text>
					</view>
					<text class="message-time">{{ msg.time || '' }}</text>
				</view>
			</view>
		</scroll-view>

		<!-- 空状态提示 -->
		<view class="empty-chat" v-else>
			<text class="empty-icon">💬</text>
			<text class="empty-title">和我聊天吧！</text>
			<text class="empty-hint">按住下方按钮说话，或点击"讲故事"</text>
		</view>

		<!-- 底部交互区 -->
		<view class="bottom-section safe-area-bottom">
			<!-- 故事分类按钮 -->
			<view class="story-categories">
				<view 
					class="story-tag" 
					v-for="cat in storyCategories" 
					:key="cat.key"
					@click="requestStoryByCategory(cat.key)"
				>
					<text class="tag-icon">{{ cat.icon }}</text>
					<text class="tag-text">{{ cat.name }}</text>
				</view>
			</view>

			<!-- 讲故事大按钮 -->
			<button 
				class="story-btn" 
				@click="requestStory"
				:disabled="isProcessing"
			>
				<text class="story-btn-icon">📖</text>
				<text class="story-btn-text">给我讲故事</text>
			</button>

			<!-- 语音交互区 -->
			<view class="voice-section">
				<view 
					class="voice-btn" 
					:class="{ 'recording': isRecording, 'processing': isProcessing }"
					@touchstart.prevent="startRecord" 
					@touchend.prevent="stopRecord"
					@click="handleClickRecord"
				>
					<view class="voice-ripple" v-if="isRecording"></view>
					<view class="voice-inner">
						<text class="voice-icon">{{ voiceIcon }}</text>
					</view>
				</view>
				<text class="voice-hint">{{ voiceLabel }}</text>
			</view>
		</view>

		<!-- 加载遮罩 -->
		<view class="loading-overlay" v-if="isProcessing">
			<view class="loading-card">
				<view class="loading-spinner"></view>
				<text class="loading-text">AI正在思考...</text>
			</view>
		</view>

		<!-- 自定义底部TabBar -->
		<view class="custom-tabbar">
			<view class="tabbar-item" @click="switchToIndex">
				<text class="tabbar-icon">📖</text>
				<text class="tabbar-text">学习</text>
			</view>
			<view class="tabbar-item active" @click="switchToChat">
				<text class="tabbar-icon">🤖</text>
				<text class="tabbar-text">AI聊天</text>
			</view>
			<view class="tabbar-item" @click="switchToProfile">
				<text class="tabbar-icon">👤</text>
				<text class="tabbar-text">我的</text>
			</view>
		</view>
	</view>
</template>

<script>
	import { getBaseURL } from '@/utils/api.js'
	
	export default {
		data() {
			return {
				messages: [],
				isRecording: false,
				isProcessing: false,
				aiEmoji: '🤖',
				aiStatus: '我在等你说话呢～',
				avatarAnimation: '',
				scrollToId: '',
				
				storyCategories: [
					{ key: 'animal', name: '动物', icon: '🐰' },
					{ key: 'fable', name: '寓言', icon: '📜' },
					{ key: 'adventure', name: '冒险', icon: '🏔️' },
					{ key: 'daily', name: '日常', icon: '🏠' }
				],
				
				// 录音相关
				recorderManager: null,
				mediaRecorder: null,
				audioChunks: [],
				audioStream: null,
				recordingSupported: true,
				
				// 音频播放
				audioContext: null,

				// H5 语音识别
				speechRecognizer: null,
				recognizedTextDraft: ''
			}
		},
		computed: {
			voiceIcon() {
				if (this.isProcessing) return '⏳'
				if (this.isRecording) return '🎤'
				return '🎙️'
			},
			voiceLabel() {
				if (this.isProcessing) return '正在处理...'
				if (this.isRecording) return '松开结束'
				return '按住说话'
			},
			statusClass() {
				if (this.isProcessing) return 'thinking'
				if (this.isRecording) return 'listening'
				return 'idle'
			}
		},
		onLoad() {
			this.initRecorder()
			this.initAudioContext()
			this.initSpeechRecognition()
		},
		onUnload() {
			if (this.audioContext) {
				this.audioContext.destroy()
				this.audioContext = null
			}
		},
		methods: {
			// TabBar 切换方法
			switchToIndex() {
				uni.switchTab({ url: '/pages/index/index' })
			},
			switchToChat() {
				// 当前页面
			},
			switchToProfile() {
				uni.switchTab({ url: '/pages/profile/profile' })
			},
			scrollToBottom() {
				if (this.messages.length > 0) {
					this.scrollToId = 'msg-' + (this.messages.length - 1)
				}
			},
			getCurrentTime() {
				const now = new Date()
				return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
			},
			initSpeechRecognition() {
				// #ifdef H5
				try {
					const SR = window.SpeechRecognition || window.webkitSpeechRecognition
					if (!SR) return
					const rec = new SR()
					rec.lang = 'zh-CN'
					rec.interimResults = true
					rec.continuous = false
					rec.onresult = (event) => {
						let finalText = ''
						let interim = ''
						for (let i = event.resultIndex; i < event.results.length; i++) {
							const t = event.results[i][0].transcript
							if (event.results[i].isFinal) finalText += t
							else interim += t
						}
						this.recognizedTextDraft = (finalText || interim || '').trim()
					}
					this.speechRecognizer = rec
				} catch (e) {
					console.warn('SpeechRecognition 不可用')
				}
				// #endif
			},
			initRecorder() {
				// #ifdef H5
				if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
					this.recordingSupported = true
					return
				}
				// #endif
				
				// #ifndef H5
				if (typeof uni.getRecorderManager !== 'function') {
					this.recordingSupported = false
					return
				}
				this.recorderManager = uni.getRecorderManager()
				this.recorderManager.onStop((res) => this.handleRecordStop(res))
				this.recorderManager.onError((err) => {
					console.error('录音错误', err)
					uni.showToast({ title: '录音失败，请检查权限', icon: 'none' })
				})
				// #endif
			},
			initAudioContext() {
				this.audioContext = uni.createInnerAudioContext()
				this.audioContext.autoplay = true
				this.audioContext.onEnded(() => {
					this.aiEmoji = '🤖'
					this.aiStatus = '我在等你说话呢～'
					this.avatarAnimation = ''
				})
				this.audioContext.onError((res) => {
					console.error('播放失败', res)
				})
			},
			handleClickRecord() {
				// #ifdef H5
				if (!this.isRecording && !this.isProcessing) {
					this.startRecord()
				} else if (this.isRecording) {
					this.stopRecord()
				}
				// #endif
			},
			async startRecord() {
				if (!this.recordingSupported || this.isProcessing) return
				
				this.isRecording = true
				this.aiEmoji = '👂'
				this.aiStatus = '我在听...'
				this.avatarAnimation = 'pulse'
				this.recognizedTextDraft = ''

				// #ifdef H5
				if (this.speechRecognizer) {
					try { this.speechRecognizer.start() } catch (e) {}
				}
				// #endif
				
				// #ifdef H5
				try {
					const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
					this.audioStream = stream
					this.audioChunks = []
					
					this.mediaRecorder = new MediaRecorder(stream, {
						mimeType: 'audio/webm;codecs=opus'
					})
					
					this.mediaRecorder.ondataavailable = (event) => {
						if (event.data.size > 0) {
							this.audioChunks.push(event.data)
						}
					}
					
					this.mediaRecorder.onstop = () => {
						if (this.audioStream) {
							this.audioStream.getTracks().forEach(track => track.stop())
							this.audioStream = null
						}
						this.handleH5RecordStop()
					}
					
					this.mediaRecorder.onerror = (err) => {
						console.error('录音错误', err)
						uni.showToast({ title: '录音失败', icon: 'none' })
						this.isRecording = false
					}
					
					this.mediaRecorder.start()
				} catch (e) {
					console.error("录音启动失败", e)
					uni.showToast({ title: '请允许麦克风权限', icon: 'none' })
					this.isRecording = false
				}
				// #endif
				
				// #ifndef H5
				if (this.recorderManager) {
					try {
						this.recorderManager.start({ format: 'mp3' })
					} catch (e) {
						console.error("录音启动失败", e)
						uni.showToast({ title: '请允许麦克风权限', icon: 'none' })
						this.isRecording = false
					}
				}
				// #endif
			},
			stopRecord() {
				if (!this.isRecording) return
				
				this.isRecording = false
				this.avatarAnimation = ''

				// #ifdef H5
				if (this.speechRecognizer) {
					try { this.speechRecognizer.stop() } catch (e) {}
				}
				// #endif
				
				// #ifdef H5
				if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
					try {
						if (typeof this.mediaRecorder.requestData === 'function') {
							this.mediaRecorder.requestData()
						}
						this.mediaRecorder.stop()
						this.isProcessing = true
					} catch (e) {
						console.error("录音停止失败", e)
					}
				}
				// #endif
				
				// #ifndef H5
				if (this.recorderManager) {
					try {
						this.recorderManager.stop()
						this.isProcessing = true
					} catch (e) {
						console.error("录音停止失败", e)
					}
				}
				// #endif
			},
			handleH5RecordStop() {
				if (this.audioChunks.length === 0) {
					this.isProcessing = false
					uni.showToast({ title: '录音为空', icon: 'none' })
					return
				}
				
				const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' })
				this.audioChunks = []
				
				const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' })
				const formData = new FormData()
				formData.append('file', audioFile)
				formData.append('mode', 'chat')
				if (this.recognizedTextDraft) {
					formData.append('text', this.recognizedTextDraft)
				}
				
				this.sendVoiceToAI(formData)
			},
			handleRecordStop(res) {
				console.log('录音结束，文件:', res.tempFilePath)
				
				uni.uploadFile({
					url: getBaseURL() + '/chat/voice',
					filePath: res.tempFilePath,
					name: 'file',
					formData: { 'mode': 'chat' },
					success: (uploadRes) => {
						if (uploadRes.statusCode === 200) {
							try {
								const result = JSON.parse(uploadRes.data)
								this.handleAIResponse(result)
							} catch (e) {
								console.error('解析失败', e)
								uni.showToast({ title: '数据解析错误', icon: 'none' })
							}
						} else {
							uni.showToast({ title: '上传失败', icon: 'none' })
						}
					},
					fail: (err) => {
						console.error('上传失败', err)
						uni.showToast({ title: '上传失败，请检查网络', icon: 'none' })
					},
					complete: () => {
						this.isProcessing = false
					}
				})
			},
			sendVoiceToAI(formData) {
				this.aiEmoji = '🤔'
				this.aiStatus = '我在思考...'
				this.avatarAnimation = 'thinking'
				
				const url = getBaseURL() + '/chat/voice'
				
				fetch(url, {
					method: 'POST',
					body: formData
				})
				.then(response => {
					if (!response.ok) {
						return response.text().then(text => {
							throw new Error(`HTTP ${response.status}: ${text}`)
						})
					}
					return response.json()
				})
				.then(result => {
					if (result && result.text) {
						this.handleAIResponse(result)
					} else {
						throw new Error('响应格式错误')
					}
				})
				.catch(err => {
					console.error('AI聊天失败', err)
					uni.showToast({ 
						title: 'AI回复失败，请重试', 
						icon: 'none',
						duration: 3000
					})
					this.aiEmoji = '😔'
					this.aiStatus = '出错了，再试一次吧'
					this.avatarAnimation = ''
				})
				.finally(() => {
					this.isProcessing = false
				})
			},
			handleAIResponse(result) {
				if (!result || !result.text) return
				
				// 添加用户消息
				if (result.recognized_text) {
					this.messages.push({
						type: 'user',
						text: result.recognized_text,
						time: this.getCurrentTime()
					})
				}
				
				// 添加AI回复
				this.messages.push({
					type: 'ai',
					text: result.text,
					time: this.getCurrentTime()
				})
				
				// 更新状态
				this.aiEmoji = '😊'
				this.aiStatus = result.title ? `故事：${result.title}` : '我说完了～'
				this.avatarAnimation = 'bounce'
				
				// 滚动到底部
				this.$nextTick(() => {
					this.scrollToBottom()
				})
				
				// 播放AI回复音频
				if (result.audio_url) {
					const url = getBaseURL() + '/' + result.audio_url
					this.playAudio(url)
				} else {
					const ttsUrl = getBaseURL() + '/tts?text=' + encodeURIComponent(result.text)
					this.playAudio(ttsUrl)
				}
			},
			requestStory() {
				this.requestStoryByCategory(null)
			},
			requestStoryByCategory(category) {
				if (this.isProcessing) return
				
				this.isProcessing = true
				this.aiEmoji = '📖'
				this.aiStatus = '让我想想讲什么故事...'
				this.avatarAnimation = 'thinking'
				
				let url = getBaseURL() + '/chat/story'
				if (category) {
					url += '?category=' + category
				}
				
				uni.request({
					url: url,
					method: 'GET',
					success: (res) => {
						if (res.statusCode === 200) {
							const result = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
							if (result && result.text) {
								this.handleAIResponse(result)
							} else {
								uni.showToast({ title: '响应格式错误', icon: 'none' })
								this.resetAIStatus()
							}
						} else {
							uni.showToast({ title: `请求失败: ${res.statusCode}`, icon: 'none' })
							this.resetAIStatus()
						}
					},
					fail: (err) => {
						console.error('请求失败:', err)
						uni.showToast({ title: '网络错误，请重试', icon: 'none' })
						this.resetAIStatus()
					},
					complete: () => {
						this.isProcessing = false
					}
				})
			},
			resetAIStatus() {
				this.aiEmoji = '😔'
				this.aiStatus = '出错了，再试一次吧'
				this.avatarAnimation = ''
			},
			playAudio(url) {
				if (!this.audioContext) {
					this.initAudioContext()
				}
				
				this.audioContext.src = url
				this.aiEmoji = '🔊'
				this.aiStatus = '正在播放...'
				this.avatarAnimation = 'speaking'
				
				const playResult = this.audioContext.play ? this.audioContext.play() : undefined
				if (playResult && typeof playResult.then === 'function') {
					playResult.catch(err => {
						console.warn('播放失败', err)
						this.aiEmoji = '🤖'
						this.aiStatus = '播放失败，但你可以看文字'
						const last = this.messages.length ? this.messages[this.messages.length - 1].text : ''
						this.fallbackSpeak(last)
					})
				}
			},
			fallbackSpeak(text) {
				if (!text) return
				// #ifdef H5
				if (typeof window !== 'undefined' && window.speechSynthesis) {
					const utter = new SpeechSynthesisUtterance(text)
					utter.lang = 'zh-CN'
					utter.rate = 0.95
					window.speechSynthesis.speak(utter)
				}
				// #endif
			}
		}
	}
</script>

<style>
	/* ========== 页面容器 ========== */
	.chat-page {
		min-height: 100vh;
		background: linear-gradient(180deg, #E8F4FD 0%, #D6EAF8 100%);
		display: flex;
		flex-direction: column;
		padding-bottom: 140rpx;
	}

	/* ========== 自定义顶部导航栏 ========== */
	.custom-navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 999;
		background: linear-gradient(145deg, #3498DB, #2980B9);
		padding-top: constant(safe-area-inset-top);
		padding-top: env(safe-area-inset-top);
	}
	
	.navbar-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 24rpx 32rpx;
	}
	
	.navbar-left {
		display: flex;
		align-items: center;
		gap: 12rpx;
	}
	
	.app-logo {
		font-size: 44rpx;
	}
	
	.app-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #FFF;
	}
	
	.navbar-right {
		background: rgba(255, 255, 255, 0.2);
		padding: 8rpx 20rpx;
		border-radius: 20rpx;
	}
	
	.status-text {
		font-size: 24rpx;
		color: #FFF;
	}

	/* ========== 自定义底部TabBar ========== */
	.custom-tabbar {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 999;
		display: flex;
		justify-content: space-around;
		align-items: center;
		height: 120rpx;
		background: #FFF;
		box-shadow: 0 -4rpx 20rpx rgba(0, 0, 0, 0.08);
		padding-bottom: constant(safe-area-inset-bottom);
		padding-bottom: env(safe-area-inset-bottom);
	}
	
	.tabbar-item {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 4rpx;
		padding: 12rpx 0;
	}
	
	.tabbar-icon {
		font-size: 44rpx;
	}
	
	.tabbar-text {
		font-size: 22rpx;
		color: #636E72;
		font-weight: 500;
	}
	
	.tabbar-item.active .tabbar-icon {
		transform: scale(1.1);
	}
	
	.tabbar-item.active .tabbar-text {
		color: #3498DB;
		font-weight: bold;
	}

	.nav-icon {
		font-size: 40rpx;
		color: #3498DB;
	}
	
	.nav-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #2D3436;
	}
	
	.nav-right {
		width: 80rpx;
	}

	/* ========== AI头像区域 ========== */
	.ai-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 32rpx;
		padding-top: calc(constant(safe-area-inset-top) + 120rpx);
		padding-top: calc(env(safe-area-inset-top) + 120rpx);
	}
	
	.ai-avatar-wrapper {
		position: relative;
	}
	
	.ai-avatar {
		width: 160rpx;
		height: 160rpx;
		background: linear-gradient(145deg, #FFF, #E8F4FD);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 12rpx 32rpx rgba(52, 152, 219, 0.2);
	}
	
	.ai-avatar.bounce {
		animation: bounce 1s ease;
	}
	
	.ai-avatar.pulse {
		animation: pulse 1s infinite;
	}
	
	.ai-avatar.thinking {
		animation: thinking 1.5s infinite;
	}
	
	.ai-avatar.speaking {
		animation: speaking 0.5s infinite;
	}
	
	@keyframes thinking {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.05) rotate(3deg); }
	}
	
	@keyframes speaking {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.03); }
	}
	
	.ai-emoji {
		font-size: 90rpx;
	}
	
	.ai-status-dot {
		position: absolute;
		bottom: 10rpx;
		right: 10rpx;
		width: 28rpx;
		height: 28rpx;
		border-radius: 50%;
		border: 4rpx solid #FFF;
	}
	
	.ai-status-dot.idle {
		background: #55EFC4;
	}
	
	.ai-status-dot.listening {
		background: #FF9F43;
		animation: pulse 1s infinite;
	}
	
	.ai-status-dot.thinking {
		background: #74B9FF;
		animation: pulse 1s infinite;
	}
	
	.ai-bubble {
		margin-top: 16rpx;
		background: #FFF;
		padding: 16rpx 28rpx;
		border-radius: 24rpx;
		box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.08);
	}
	
	.ai-bubble text {
		font-size: 28rpx;
		color: #2D3436;
		font-weight: 600;
	}

	/* ========== 对话历史 ========== */
	.chat-history {
		flex: 1;
		padding: 16rpx 32rpx;
		max-height: 400rpx;
	}
	
	.message-item {
		display: flex;
		gap: 16rpx;
		margin-bottom: 24rpx;
		animation: fadeIn 0.3s ease;
	}
	
	.message-item.user {
		flex-direction: row-reverse;
	}
	
	.message-avatar {
		width: 64rpx;
		height: 64rpx;
		background: #FFF;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 32rpx;
		box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
		flex-shrink: 0;
	}
	
	.message-content {
		max-width: 70%;
	}
	
	.message-bubble {
		padding: 20rpx 28rpx;
		border-radius: 28rpx;
		box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.06);
	}
	
	.message-item.user .message-bubble {
		background: linear-gradient(145deg, #3498DB, #2980B9);
		border-bottom-right-radius: 8rpx;
	}
	
	.message-item.ai .message-bubble {
		background: #FFF;
		border-bottom-left-radius: 8rpx;
	}
	
	.message-item.user .message-text {
		color: #FFF;
	}
	
	.message-item.ai .message-text {
		color: #2D3436;
	}
	
	.message-text {
		font-size: 28rpx;
		line-height: 1.6;
	}
	
	.message-time {
		font-size: 22rpx;
		color: #B2BEC3;
		margin-top: 8rpx;
		display: block;
	}
	
	.message-item.user .message-time {
		text-align: right;
	}

	/* ========== 空状态 ========== */
	.empty-chat {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 48rpx;
	}
	
	.empty-icon {
		font-size: 80rpx;
		margin-bottom: 24rpx;
	}
	
	.empty-title {
		font-size: 32rpx;
		font-weight: bold;
		color: #2D3436;
	}
	
	.empty-hint {
		font-size: 26rpx;
		color: #636E72;
		margin-top: 12rpx;
		text-align: center;
	}

	/* ========== 底部交互区 ========== */
	.bottom-section {
		padding: 24rpx 32rpx 48rpx;
		background: linear-gradient(180deg, transparent 0%, rgba(255, 255, 255, 0.9) 100%);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24rpx;
	}
	
	/* 故事分类 */
	.story-categories {
		display: flex;
		gap: 16rpx;
		flex-wrap: wrap;
		justify-content: center;
	}
	
	.story-tag {
		display: flex;
		align-items: center;
		gap: 8rpx;
		background: #FFF;
		padding: 12rpx 24rpx;
		border-radius: 24rpx;
		box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.06);
		transition: all 0.2s;
	}
	
	.story-tag:active {
		transform: scale(0.96);
		background: #E8F4FD;
	}
	
	.tag-icon {
		font-size: 28rpx;
	}
	
	.tag-text {
		font-size: 24rpx;
		font-weight: 600;
		color: #2D3436;
	}
	
	/* 讲故事按钮 */
	.story-btn {
		width: 80%;
		height: 100rpx;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		color: #FFF;
		border: none;
		border-radius: 50rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 16rpx;
		box-shadow: 0 8rpx 0 #C44A34, 0 12rpx 24rpx rgba(255, 159, 67, 0.3);
		transition: all 0.15s;
	}
	
	.story-btn:active {
		transform: translateY(6rpx);
		box-shadow: 0 2rpx 0 #C44A34;
	}
	
	.story-btn:disabled {
		opacity: 0.6;
	}
	
	.story-btn-icon {
		font-size: 40rpx;
	}
	
	.story-btn-text {
		font-size: 32rpx;
		font-weight: bold;
	}
	
	/* 语音按钮区 */
	.voice-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12rpx;
	}
	
	.voice-btn {
		width: 140rpx;
		height: 140rpx;
		border-radius: 50%;
		background: linear-gradient(145deg, #3498DB, #2980B9);
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 10rpx 24rpx rgba(52, 152, 219, 0.4);
		position: relative;
		transition: all 0.2s;
	}
	
	.voice-btn:active {
		transform: scale(0.96);
	}
	
	.voice-btn.recording {
		background: linear-gradient(145deg, #FF6B6B, #D63031);
		animation: glow-red 1s infinite;
	}
	
	.voice-btn.processing {
		background: #B2BEC3;
		box-shadow: none;
	}
	
	@keyframes glow-red {
		0%, 100% { box-shadow: 0 0 30rpx rgba(255, 107, 107, 0.4); }
		50% { box-shadow: 0 0 60rpx rgba(255, 107, 107, 0.8); }
	}
	
	.voice-ripple {
		position: absolute;
		inset: -16rpx;
		border-radius: 50%;
		border: 4rpx solid rgba(255, 107, 107, 0.5);
		animation: ripple 1.5s infinite;
	}
	
	.voice-inner {
		width: 110rpx;
		height: 110rpx;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.2);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.voice-icon {
		font-size: 56rpx;
	}
	
	.voice-hint {
		font-size: 26rpx;
		color: #636E72;
		font-weight: 600;
	}

	/* ========== 加载遮罩 ========== */
	.loading-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	
	.loading-card {
		background: #FFF;
		padding: 48rpx 64rpx;
		border-radius: 32rpx;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24rpx;
	}
	
	.loading-spinner {
		width: 64rpx;
		height: 64rpx;
		border: 6rpx solid rgba(52, 152, 219, 0.2);
		border-top-color: #3498DB;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	
	.loading-text {
		font-size: 28rpx;
		color: #636E72;
	}

	/* ========== 动画 ========== */
	@keyframes bounce {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-16rpx); }
	}
	
	@keyframes pulse {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.08); }
	}
	
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(20rpx); }
		to { opacity: 1; transform: translateY(0); }
	}
	
	@keyframes ripple {
		to { transform: scale(1.5); opacity: 0; }
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
