<template>
	<view class="learn-page" :class="{ 'dark-mode': isDarkMode }">
		<!-- 顶部导航栏 -->
		<view class="nav-header safe-area-top">
			<view class="nav-left" @click="goBack">
				<text class="nav-icon">←</text>
			</view>
			<view class="nav-center">
				<text class="nav-title">语言学习</text>
			</view>
			<view class="nav-right">
				<text class="progress-text">{{ currentIndex + 1 }}/{{ totalCount }}</text>
			</view>
		</view>

		<!-- 进度条 -->
		<view class="progress-wrapper">
			<view class="progress-track">
				<view class="progress-fill" :style="{ width: progressPercent + '%' }">
					<view class="progress-glow"></view>
				</view>
			</view>
			<view class="progress-stars">
				<text v-for="i in 3" :key="i" class="star-icon" :class="{ 'earned': starCount >= i }">
					{{ starCount >= i ? '⭐' : '☆' }}
				</text>
			</view>
		</view>

		<!-- 吉祥物区域 -->
		<view class="mascot-section">
			<view class="mascot-avatar" :class="mascotAnimation">
				<text class="mascot-emoji">{{ currentEmoji }}</text>
			</view>
			<view class="speech-bubble" v-if="mascotMessage">
				<view class="bubble-content">
					<text>{{ mascotMessage }}</text>
				</view>
				<view class="bubble-arrow"></view>
			</view>
		</view>

		<!-- 核心学习卡片 -->
		<view class="word-card-wrapper">
			<view class="word-card" :class="{ 'card-success': hasResult && score >= 80, 'card-warning': hasResult && score < 60, 'card-shake': strategyAdjusted }">
				<!-- 卡片装饰 -->
				<view class="card-decoration top-left"></view>
				<view class="card-decoration top-right"></view>
				
				<!-- 词汇内容 -->
				<view class="word-content">
					<text class="pinyin-text">{{ currentWord.pinyin }}</text>
					<text class="hanzi-text">{{ currentWord.text }}</text>
					<view class="word-divider"></view>
					<view class="word-tip-box" v-if="currentWord.tip">
						<text class="tip-icon">💡</text>
						<text class="tip-text">{{ currentWord.tip }}</text>
					</view>
				</view>
				
				<!-- 听一听按钮 -->
				<view class="listen-btn" @click="playStandard">
					<text class="listen-icon">🔊</text>
					<text class="listen-text">听一听</text>
					<view class="listen-ripple" v-if="isPlaying"></view>
				</view>
			</view>
		</view>

		<!-- 反馈结果面板 -->
		<view class="feedback-panel" v-if="hasResult" :class="feedbackClass">
			<view class="feedback-header">
				<view class="star-display">
					<text v-for="n in 3" :key="n" class="feedback-star" :class="{ 'active': n <= starCount }">
						{{ n <= starCount ? '⭐' : '☆' }}
					</text>
				</view>
				<view class="score-badge">
					<text class="score-number">{{ score }}</text>
					<text class="score-label">分</text>
				</view>
			</view>
			
			<text class="feedback-text">{{ feedbackText }}</text>
			
			<!-- 自适应鼓励语 -->
			<view class="encouragement-box" v-if="encouragement">
				<text class="encouragement-icon">💪</text>
				<text class="encouragement-text">{{ encouragement }}</text>
			</view>
			
			<!-- 改进提示列表 -->
			<view class="improvement-section" v-if="improvementTips.length">
				<text class="improvement-title">改进建议：</text>
				<view class="improvement-list">
					<view class="improvement-item" v-for="(tip, index) in improvementTips" :key="index">
						<text class="improvement-dot">•</text>
						<text class="improvement-text">{{ tip.message || tip }}</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 底部控制区 -->
		<view class="bottom-controls safe-area-bottom">
			<!-- 录音按钮 -->
			<view class="mic-button-wrapper">
				<view 
					class="mic-button" 
					:class="{ 'recording': isRecording, 'disabled': !recordingSupported }"
					@touchstart.prevent="startRecord" 
					@touchend.prevent="stopRecord"
				>
					<view class="mic-pulse" v-if="isRecording"></view>
					<view class="mic-inner">
						<text class="mic-icon">{{ isRecording ? '🎤' : '🎙️' }}</text>
					</view>
				</view>
				<text class="mic-hint">{{ isRecording ? '松开结束' : '按住说话' }}</text>
			</view>

			<!-- H5点击录音按钮 -->
			<!-- #ifdef H5 -->
			<button class="h5-record-btn" @click="toggleRecord">
				<text class="h5-btn-icon">{{ isRecording ? '⏹️' : '▶️' }}</text>
				<text class="h5-btn-text">{{ isRecording ? '点击停止' : '点击录音' }}</text>
			</button>
			<!-- #endif -->
			
			<!-- 操作按钮组 -->
			<view class="action-buttons" v-if="hasResult">
				<button class="action-btn primary" @click="retryWord">
					<text class="btn-emoji">🔁</text>
					<text>再练一次</text>
				</button>
				
				<button class="action-btn secondary" v-if="showListenAgain" @click="playStandard">
					<text class="btn-emoji">👂</text>
					<text>再听一次</text>
				</button>
				
				<button class="action-btn warning" v-if="strategyAdjusted" @click="swapWord">
					<text class="btn-emoji">🎯</text>
					<text>换一题</text>
				</button>
				
				<button class="action-btn break" v-if="showBreakButton" @click="takeBreak">
					<text class="btn-emoji">☕</text>
					<text>休息一下</text>
				</button>
			</view>
			
			<!-- 下一题按钮 -->
			<button class="next-btn" v-if="hasResult" @click="nextWord">
				<text>下一题</text>
				<text class="next-arrow">→</text>
			</button>
		</view>

		<!-- 加载遮罩 -->
		<view class="loading-overlay" v-if="isAnalyzing">
			<view class="loading-content">
				<view class="loading-spinner"></view>
				<text class="loading-text">正在分析发音...</text>
			</view>
		</view>
	</view>
</template>

<script>
	import { buildURL, apiFetch, fetchCourses, getUserId } from '@/utils/api.js'
	
	// 常量配置
	const EMOJI_MAP = {
		default: '🙂',
		listening: '👂',
		recording: '🎤',
		happy: '😆',
		confused: '🤔',
		celebrate: '🎉',
		thinking: '🤔',
		speaking: '🗣️'
	}
	
	export default {
		data() {
			return {
				courseId: 0,
				words: [],
				currentIndex: 0,
				isRecording: false,
				isPlaying: false,
				isAnalyzing: false,
				recordingSupported: true,
				hasResult: false,
				score: 0,
				isDarkMode: false,
				
				// 状态
				currentEmoji: EMOJI_MAP.default,
				mascotMessage: '跟我读一遍～',
				mascotAnimation: '',
				strategyAdjusted: false,
				lastEmotionType: 'neutral',
				feedbackText: '',
				starCount: 0,
				improvementTips: [],
				encouragement: '',
				showListenAgain: false,
				showBreakButton: false,
				attemptCount: 0,
				
				audioContext: null,
				// H5 录音相关
				mediaRecorder: null,
				audioChunks: [],
				audioStream: null
			}
		},
		computed: {
			currentWord() {
				return this.words[this.currentIndex] || { text: '', pinyin: '', tip: '' }
			},
			totalCount() {
				return this.words.length || 1
			},
			progressPercent() {
				return Math.round(((this.currentIndex + 1) / this.totalCount) * 100)
			},
			feedbackClass() {
				if (this.score >= 80) return 'feedback-success'
				if (this.score >= 60) return 'feedback-normal'
				return 'feedback-warning'
			}
		},
		onLoad(options) {
			this.courseId = options.id || 1
			const content = uni.getStorageSync('current_course_content')
			console.log('加载课程内容:', content)
			
			if (content && Array.isArray(content) && content.length > 0) {
				this.words = content
			} else {
				console.warn('未找到存储的课程内容，使用默认数据')
				this.words = [{ text: '你好', pinyin: 'nǐ hǎo', tip: '微笑点头打招呼' }]
				this.fetchCourseContent()
			}
			
			this.initRecorder()
			this.initAudioContext()
			this.schedulePlayStandard()
		},
		onShow() {
			if (!this.audioContext) {
				this.initAudioContext()
			}
			this.schedulePlayStandard()
		},
		onHide() {
			if (this.audioContext) {
				this.audioContext.stop()
			}
		},
		onUnload() {
			if (this.audioContext) {
				this.audioContext.destroy()
				this.audioContext = null
			}
			clearTimeout(this.playTimer)
		},
		methods: {
			goBack() {
				uni.navigateBack()
			},
			async toggleRecord() {
				if (this.isRecording) {
					this.stopRecord()
				} else {
					await this.startRecord()
				}
			},
			initRecorder() {
				// #ifdef H5
				if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
					this.recordingSupported = true
					this.recorderManager = null
					return
				}
				// #endif
				
				// #ifndef H5
				if (typeof uni.getRecorderManager !== 'function') {
					this.recordingSupported = false
					uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
					return
				}
				this.recorderManager = uni.getRecorderManager()
				if (!this.recorderManager) {
					this.recordingSupported = false
					uni.showToast({ title: '录音模块不可用', icon: 'none' })
					return
				}
				this.recordingSupported = true
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
				this.audioContext.onPlay(() => {
					this.isPlaying = true
				})
				this.audioContext.onEnded(() => {
					this.isPlaying = false
					this.currentEmoji = '🙂'
					this.mascotMessage = '该你了～'
					if (this._afterPlayCallback) {
						this._afterPlayCallback()
						this._afterPlayCallback = null
					}
				})
				this.audioContext.onError((res) => {
					this.isPlaying = false
					console.error('播放失败', res)
				})
			},
			schedulePlayStandard() {
				clearTimeout(this.playTimer)
				this.playTimer = setTimeout(() => {
					this.playStandard()
				}, 300)
			},
			playStandard() {
				this.mascotMessage = '注意听哦～'
				this.currentEmoji = '👂'
				this.mascotAnimation = 'bounce'
				
				const text = this.currentWord.text || '你好'
				const url = `${buildURL('/tts')}?text=${encodeURIComponent(text)}&t=${new Date().getTime()}`
				
				this.playAudio(url, () => {
					this.currentEmoji = '🙂'
					this.mascotMessage = '该你了～'
					this.mascotAnimation = ''
				}, text)
			},
			async startRecord() {
				if (!this.recordingSupported) {
					uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
					return
				}
				
				this.isRecording = true
				this.hasResult = false
				this.strategyAdjusted = false
				this.currentEmoji = '🎤'
				this.mascotMessage = '正在听...'
				this.mascotAnimation = 'pulse'
				
				if (typeof uni.vibrateShort === 'function') {
					uni.vibrateShort({ success: () => {}, fail: () => {} })
				}
				
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
				if (!this.recorderManager || typeof this.recorderManager.start !== 'function') {
					uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
					this.isRecording = false
					return
				}
				try {
					this.recorderManager.start({ format: 'mp3' })
				} catch (e) {
					console.error("录音启动失败", e)
					uni.showToast({ title: '请允许麦克风权限', icon: 'none' })
					this.isRecording = false
				}
				// #endif
			},
			stopRecord() {
				if (!this.isRecording) return
				
				this.isRecording = false
				this.mascotAnimation = ''
				
				// #ifdef H5
				if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
					try {
						if (typeof this.mediaRecorder.requestData === 'function') {
							this.mediaRecorder.requestData()
						}
						this.mediaRecorder.stop()
						this.isAnalyzing = true
					} catch (e) {
						console.error("录音停止失败", e)
					}
				}
				// #endif
				
				// #ifndef H5
				if (!this.recordingSupported || !this.recorderManager || typeof this.recorderManager.stop !== 'function') {
					return
				}
				try {
					this.recorderManager.stop()
					this.isAnalyzing = true
				} catch (e) {
					console.error("录音停止失败", e)
				}
				// #endif
			},
			handleH5RecordStop() {
				if (this.audioChunks.length === 0) {
					this.isAnalyzing = false
					uni.showToast({ title: '录音为空', icon: 'none' })
					return
				}
				
				const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' })
				this.audioChunks = []
				
				const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' })
				
				const formData = new FormData()
				formData.append('file', audioFile)
				formData.append('course_id', this.courseId.toString())
				formData.append('user_id', getUserId().toString())
				formData.append('word_text', this.currentWord.text || '')
				formData.append('attempt_count', (this.attemptCount + 1).toString())
				
				const controller = new AbortController()
				const timeoutId = setTimeout(() => controller.abort(), 30000)
				
				fetch(buildURL('/analyze'), {
					method: 'POST',
					body: formData,
					signal: controller.signal
				})
				.then(response => {
					clearTimeout(timeoutId)
					if (!response.ok) {
						return response.text().then(text => {
							console.error('后端错误响应:', text)
							throw new Error(`HTTP error! status: ${response.status}`)
						})
					}
					return response.json()
				})
				.then(result => {
					console.log('后端返回:', result)
					if (!result || typeof result !== 'object') {
						throw new Error('后端返回数据格式错误')
					}
					this.showResult(result)
				})
				.catch(err => {
					clearTimeout(timeoutId)
					console.error('上传失败', err)
					if (err.name === 'AbortError') {
						uni.showToast({ title: '分析超时，请重试', icon: 'none' })
					} else {
						uni.showToast({ title: '上传失败，请重试', icon: 'none', duration: 3000 })
					}
				})
				.finally(() => {
					this.isAnalyzing = false
				})
			},
			handleRecordStop(res) {
				console.log('录音结束，文件:', res.tempFilePath)
				uni.uploadFile({
					url: buildURL('/analyze'),
					filePath: res.tempFilePath,
					name: 'file',
					formData: {
						'course_id': this.courseId,
						'user_id': getUserId(),
						'word_text': this.currentWord.text || '',
						'attempt_count': this.attemptCount + 1
					},
					success: (uploadFileRes) => {
						if (uploadFileRes.statusCode !== 200) {
							this.handleAnalysisError(uploadFileRes)
							return
						}
						try {
							const result = JSON.parse(uploadFileRes.data)
							this.showResult(result)
						} catch (e) {
							console.error('解析失败', e)
							uni.showToast({ title: '数据解析错误', icon: 'none' })
						}
					},
					fail: (err) => {
						console.error('上传失败', err)
						uni.showToast({ title: '上传失败，请检查网络', icon: 'none' })
					},
					complete: () => {
						this.isAnalyzing = false
					}
				})
			},
			showResult(result) {
				this.hasResult = true
				this.score = result.score
				this.attemptCount++
				
				if (Array.isArray(result.issues)) {
					this.improvementTips = result.issues.slice(0, 3)
				} else {
					this.improvementTips = []
				}
				
				this.lastEmotionType = (result.emotion && result.emotion.type) ? result.emotion.type : 'neutral'
				const isNegative = ['confused', 'frustrated'].includes(this.lastEmotionType) || result.score < 60
				
				if (result.adaptive) {
					this.encouragement = result.adaptive.strategy_message || ''
					this.showListenAgain = result.adaptive.show_retry_button || isNegative
					this.showBreakButton = result.adaptive.show_break_button || false
					
					if (result.adaptive.auto_demo && !result.feedback_audio) {
						setTimeout(() => this.schedulePlayStandard(), 1000)
					}
				} else {
					this.encouragement = result.emotion?.encouragement || ''
					this.showListenAgain = isNegative
					this.showBreakButton = this.attemptCount >= 5
				}
				
				if (result.feedback_audio) {
					const url = buildURL('/' + result.feedback_audio)
					const after = isNegative ? () => this.schedulePlayStandard() : null
					this.playAudio(url, after, result.feedback)
				}

				if (result.score >= 80) this.starCount = 3
				else if (result.score >= 60) this.starCount = 2
				else this.starCount = 1

				if (result.emotion.type === 'happy' || result.score >= 80) {
					this.currentEmoji = '😆'
					this.mascotMessage = '太棒啦！'
					this.mascotAnimation = 'bounce'
					this.feedbackText = result.feedback || result.emotion.tip || '发音很标准！'
				} else if (['confused', 'frustrated'].includes(result.emotion.type) || result.score < 60) {
					this.currentEmoji = '🤗'
					this.mascotMessage = '没关系，我们慢一点～'
					this.feedbackText = result.feedback || result.emotion?.tip || '再来一次，你可以的！'
					this.strategyAdjusted = true

					if (!result.feedback_audio) {
						setTimeout(() => this.schedulePlayStandard(), 900)
					}
				} else {
					this.currentEmoji = '🙂'
					this.mascotMessage = '继续加油！'
					this.feedbackText = result.feedback || result.emotion.tip || '读得不错哦'
				}
				
				if (this.starCount >= 2) {
					let stars = uni.getStorageSync('user_stars') || 0
					uni.setStorageSync('user_stars', stars + this.starCount)
				}
			},
			retryWord() {
				this.resetState(false)
				this.mascotMessage = '再来一次～先听再读'
				this.schedulePlayStandard()
			},
			swapWord() {
				if (!Array.isArray(this.words) || this.words.length <= 1) return
				let next = this.currentIndex
				let guard = 0
				while (next === this.currentIndex && guard < 10) {
					next = Math.floor(Math.random() * this.words.length)
					guard++
				}
				this.currentIndex = next
				this.resetState(true)
				this.mascotMessage = '换一个更轻松的～'
				this.schedulePlayStandard()
			},
			takeBreak() {
				this.currentEmoji = '☕'
				this.mascotMessage = '休息一下，喝点水再继续！'
				uni.showModal({
					title: '休息时间 ☕',
					content: '你学习得很努力！休息一下，活动活动，稍后再继续吧！',
					confirmText: '继续学习',
					cancelText: '结束课程',
					success: (res) => {
						if (res.confirm) {
							this.resetState(true)
							this.schedulePlayStandard()
						} else {
							uni.navigateBack()
						}
					}
				})
			},
			nextWord() {
				if (this.currentIndex < this.words.length - 1) {
					this.currentIndex++
					this.resetState()
					setTimeout(() => this.playStandard(), 500)
				} else {
					this.currentEmoji = '🎉'
					this.mascotMessage = '课程完成！'
					uni.showModal({
						title: '🎉 通关啦！',
						content: '你真棒！获得了好多星星！',
						showCancel: false,
						success: () => uni.navigateBack()
					})
				}
			},
			resetState(resetAttempts = true) {
				this.hasResult = false
				this.strategyAdjusted = false
				this.currentEmoji = '🙂'
				this.mascotMessage = '跟我读一遍～'
				this.mascotAnimation = ''
				this.starCount = 0
				this.improvementTips = []
				this.encouragement = ''
				this.showListenAgain = false
				this.showBreakButton = false
				if (resetAttempts) {
					this.attemptCount = 0
				}
			},
			playAudio(url, onEndedCallback, fallbackText = '') {
				if (!this.audioContext) {
					this.initAudioContext()
				}
				this._afterPlayCallback = onEndedCallback || null
				
				this.audioContext.src = url
				
				const playResult = this.audioContext.play ? this.audioContext.play() : undefined
				if (playResult && typeof playResult.then === 'function') {
					playResult.catch(err => {
						console.warn('浏览器阻止自动播放或资源不可用，使用本地语音', err)
						this.fallbackSpeak(fallbackText)
					})
				} else if (!playResult) {
					setTimeout(() => {
						if (this.audioContext && this.audioContext.paused && fallbackText) {
							this.fallbackSpeak(fallbackText)
						}
					}, 500)
				}
			},
			fallbackSpeak(text) {
				if (!text) return
				if (typeof window !== 'undefined' && window.speechSynthesis) {
					const synth = window.speechSynthesis
					const utter = new SpeechSynthesisUtterance(text)
					utter.lang = 'zh-CN'
					utter.rate = 0.9
					synth.speak(utter)
				} else {
					uni.showToast({ title: '语音不可用', icon: 'none' })
				}
			},
			handleAnalysisError(uploadFileRes) {
				let message = '分析失败，请重新录制'
				try {
					const payload = JSON.parse(uploadFileRes.data || '{}')
					if (payload.detail) {
						message = payload.detail
					}
				} catch (err) {
					console.warn('错误信息解析失败', err)
				}
				uni.showToast({ title: message, icon: 'none' })
			},
			async fetchCourseContent() {
				try {
					const courses = await fetchCourses()
					if (Array.isArray(courses)) {
						const course = courses.find(c => c.id == this.courseId) || courses[0]
						if (course && course.content_json) {
							const content = JSON.parse(course.content_json)
							if (Array.isArray(content) && content.length > 0) {
								this.words = content
								uni.setStorageSync('current_course_content', content)
								this.resetState()
								this.schedulePlayStandard()
							}
						}
					}
				} catch (err) {
					console.warn('获取课程内容失败:', err.message)
				}
			}
		}
	}
</script>

<style>
	/* ========== 页面容器 ========== */
	.learn-page {
		min-height: 100vh;
		background: linear-gradient(180deg, #FFF5E6 0%, #FFE4CC 50%, #FFDAB9 100%);
		display: flex;
		flex-direction: column;
		position: relative;
		overflow-x: hidden;
	}

	/* ========== 顶部导航 ========== */
	.nav-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 24rpx 32rpx;
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(20rpx);
		position: sticky;
		top: 0;
		z-index: 100;
	}
	
	.nav-left {
		width: 80rpx;
		height: 80rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #FFF;
		border-radius: 50%;
		box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
	}
	
	.nav-icon {
		font-size: 40rpx;
		color: #FF9F43;
	}
	
	.nav-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #2D3436;
	}
	
	.progress-text {
		font-size: 28rpx;
		font-weight: bold;
		color: #FF9F43;
		background: #FFF5E6;
		padding: 8rpx 20rpx;
		border-radius: 20rpx;
	}

	/* ========== 进度条 ========== */
	.progress-wrapper {
		padding: 20rpx 32rpx;
	}
	
	.progress-track {
		height: 16rpx;
		background: rgba(255, 255, 255, 0.6);
		border-radius: 10rpx;
		overflow: hidden;
		box-shadow: inset 0 2rpx 4rpx rgba(0, 0, 0, 0.05);
	}
	
	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #FF9F43, #FF6B6B);
		border-radius: 10rpx;
		transition: width 0.4s ease;
		position: relative;
	}
	
	.progress-glow {
		position: absolute;
		right: 0;
		top: 50%;
		transform: translateY(-50%);
		width: 20rpx;
		height: 20rpx;
		background: #FFF;
		border-radius: 50%;
		box-shadow: 0 0 20rpx rgba(255, 159, 67, 0.8);
	}
	
	.progress-stars {
		display: flex;
		justify-content: center;
		gap: 16rpx;
		margin-top: 12rpx;
	}
	
	.star-icon {
		font-size: 32rpx;
		opacity: 0.4;
		transition: all 0.3s;
	}
	
	.star-icon.earned {
		opacity: 1;
		transform: scale(1.2);
	}

	/* ========== 吉祥物区域 ========== */
	.mascot-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 24rpx;
		min-height: 200rpx;
	}
	
	.mascot-avatar {
		width: 140rpx;
		height: 140rpx;
		background: linear-gradient(145deg, #FFF, #FFF5E6);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 8rpx 24rpx rgba(255, 159, 67, 0.3);
	}
	
	.mascot-avatar.bounce {
		animation: bounce 1s infinite;
	}
	
	.mascot-avatar.pulse {
		animation: pulse 1s infinite;
	}
	
	.mascot-emoji {
		font-size: 80rpx;
	}
	
	.speech-bubble {
		margin-top: 16rpx;
		position: relative;
		animation: fadeIn 0.3s ease;
	}
	
	.bubble-content {
		background: #FFF;
		padding: 16rpx 28rpx;
		border-radius: 24rpx;
		box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.1);
	}
	
	.bubble-content text {
		font-size: 28rpx;
		color: #2D3436;
		font-weight: 600;
	}
	
	.bubble-arrow {
		position: absolute;
		top: -12rpx;
		left: 50%;
		transform: translateX(-50%);
		width: 0;
		height: 0;
		border-left: 16rpx solid transparent;
		border-right: 16rpx solid transparent;
		border-bottom: 16rpx solid #FFF;
	}

	/* ========== 核心学习卡片 ========== */
	.word-card-wrapper {
		padding: 0 32rpx;
		flex: 1;
		display: flex;
		align-items: flex-start;
	}
	
	.word-card {
		width: 100%;
		background: #FFF;
		border-radius: 40rpx;
		padding: 48rpx 32rpx;
		box-shadow: 0 12rpx 40rpx rgba(255, 159, 67, 0.2);
		position: relative;
		overflow: hidden;
		transition: all 0.3s ease;
	}
	
	.word-card.card-success {
		border: 4rpx solid #55EFC4;
		box-shadow: 0 12rpx 40rpx rgba(85, 239, 196, 0.3);
	}
	
	.word-card.card-warning {
		border: 4rpx solid #FDCB6E;
	}
	
	.word-card.card-shake {
		animation: shake 0.5s ease;
	}
	
	.card-decoration {
		position: absolute;
		width: 100rpx;
		height: 100rpx;
		border-radius: 50%;
		opacity: 0.1;
	}
	
	.card-decoration.top-left {
		top: -30rpx;
		left: -30rpx;
		background: #FF9F43;
	}
	
	.card-decoration.top-right {
		top: -30rpx;
		right: -30rpx;
		background: #00CEC9;
	}
	
	.word-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
	}
	
	.pinyin-text {
		font-size: 36rpx;
		color: #636E72;
		letter-spacing: 4rpx;
		margin-bottom: 12rpx;
	}
	
	.hanzi-text {
		font-size: 120rpx;
		font-weight: 900;
		color: #2D3436;
		line-height: 1.2;
		text-shadow: 2rpx 2rpx 0 rgba(0, 0, 0, 0.05);
	}
	
	.word-divider {
		width: 80rpx;
		height: 6rpx;
		background: linear-gradient(90deg, #FF9F43, #FF6B6B);
		border-radius: 3rpx;
		margin: 24rpx 0;
	}
	
	.word-tip-box {
		display: flex;
		align-items: center;
		gap: 12rpx;
		background: #FFF9E6;
		padding: 16rpx 28rpx;
		border-radius: 24rpx;
		margin-top: 8rpx;
	}
	
	.tip-icon {
		font-size: 28rpx;
	}
	
	.tip-text {
		font-size: 26rpx;
		color: #F39C12;
	}
	
	.listen-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12rpx;
		margin-top: 32rpx;
		padding: 20rpx 40rpx;
		background: linear-gradient(145deg, #E8F8F5, #D1F2EB);
		border-radius: 40rpx;
		position: relative;
		transition: all 0.2s;
	}
	
	.listen-btn:active {
		transform: scale(0.96);
	}
	
	.listen-icon {
		font-size: 36rpx;
	}
	
	.listen-text {
		font-size: 28rpx;
		font-weight: bold;
		color: #00B894;
	}
	
	.listen-ripple {
		position: absolute;
		inset: 0;
		border-radius: 40rpx;
		border: 2rpx solid #00B894;
		animation: ripple 1s infinite;
	}

	/* ========== 反馈面板 ========== */
	.feedback-panel {
		margin: 24rpx 32rpx;
		padding: 24rpx;
		background: #FFF;
		border-radius: 28rpx;
		box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.08);
		animation: fadeIn 0.3s ease;
	}
	
	.feedback-panel.feedback-success {
		border-left: 8rpx solid #55EFC4;
	}
	
	.feedback-panel.feedback-normal {
		border-left: 8rpx solid #FDCB6E;
	}
	
	.feedback-panel.feedback-warning {
		border-left: 8rpx solid #FF7675;
	}
	
	.feedback-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16rpx;
	}
	
	.star-display {
		display: flex;
		gap: 8rpx;
	}
	
	.feedback-star {
		font-size: 40rpx;
		opacity: 0.3;
		transition: all 0.3s;
	}
	
	.feedback-star.active {
		opacity: 1;
		animation: bounce 0.5s ease;
	}
	
	.score-badge {
		display: flex;
		align-items: baseline;
		gap: 4rpx;
		background: linear-gradient(145deg, #FF9F43, #FF6B6B);
		padding: 8rpx 20rpx;
		border-radius: 20rpx;
	}
	
	.score-number {
		font-size: 36rpx;
		font-weight: bold;
		color: #FFF;
	}
	
	.score-label {
		font-size: 22rpx;
		color: rgba(255, 255, 255, 0.9);
	}
	
	.feedback-text {
		font-size: 30rpx;
		font-weight: 600;
		color: #2D3436;
		display: block;
		margin-bottom: 12rpx;
	}
	
	.encouragement-box {
		display: flex;
		align-items: center;
		gap: 12rpx;
		background: #FFF9E6;
		padding: 16rpx 20rpx;
		border-radius: 16rpx;
		margin-top: 12rpx;
	}
	
	.encouragement-icon {
		font-size: 28rpx;
	}
	
	.encouragement-text {
		font-size: 26rpx;
		color: #F39C12;
		flex: 1;
	}
	
	.improvement-section {
		margin-top: 16rpx;
		padding-top: 16rpx;
		border-top: 2rpx dashed rgba(0, 0, 0, 0.08);
	}
	
	.improvement-title {
		font-size: 26rpx;
		color: #636E72;
		font-weight: 600;
	}
	
	.improvement-list {
		margin-top: 8rpx;
	}
	
	.improvement-item {
		display: flex;
		align-items: flex-start;
		gap: 12rpx;
		margin-top: 8rpx;
	}
	
	.improvement-dot {
		color: #FF7675;
		font-weight: bold;
	}
	
	.improvement-text {
		font-size: 24rpx;
		color: #636E72;
		flex: 1;
		line-height: 1.5;
	}

	/* ========== 底部控制区 ========== */
	.bottom-controls {
		padding: 24rpx 32rpx 48rpx;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24rpx;
		background: linear-gradient(180deg, transparent, rgba(255, 218, 185, 0.8));
	}
	
	.mic-button-wrapper {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12rpx;
	}
	
	.mic-button {
		width: 160rpx;
		height: 160rpx;
		border-radius: 50%;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 12rpx 32rpx rgba(255, 159, 67, 0.4);
		position: relative;
		transition: all 0.2s ease;
	}
	
	.mic-button:active {
		transform: scale(0.95);
	}
	
	.mic-button.recording {
		background: linear-gradient(145deg, #FF6B6B, #D63031);
		animation: glow 1s infinite;
	}
	
	.mic-button.disabled {
		background: #B2BEC3;
		box-shadow: none;
	}
	
	.mic-pulse {
		position: absolute;
		inset: -20rpx;
		border-radius: 50%;
		border: 4rpx solid rgba(255, 107, 107, 0.5);
		animation: ripple 1.5s infinite;
	}
	
	.mic-inner {
		width: 130rpx;
		height: 130rpx;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.2);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.mic-icon {
		font-size: 60rpx;
	}
	
	.mic-hint {
		font-size: 26rpx;
		color: #636E72;
		font-weight: 600;
	}
	
	/* H5录音按钮 */
	.h5-record-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12rpx;
		background: #FFF;
		border: 2rpx solid #FF9F43;
		border-radius: 40rpx;
		padding: 16rpx 40rpx;
		margin-top: -8rpx;
	}
	
	.h5-btn-icon {
		font-size: 28rpx;
	}
	
	.h5-btn-text {
		font-size: 28rpx;
		color: #FF9F43;
		font-weight: 600;
	}
	
	/* 操作按钮组 */
	.action-buttons {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 16rpx;
		width: 100%;
	}
	
	.action-btn {
		display: flex;
		align-items: center;
		gap: 8rpx;
		padding: 16rpx 28rpx;
		border-radius: 32rpx;
		font-size: 26rpx;
		font-weight: 600;
		border: none;
		transition: all 0.2s;
		min-height: 80rpx;
	}
	
	.action-btn:active {
		transform: scale(0.96);
	}
	
	.action-btn.primary {
		background: #E8F8F5;
		color: #00B894;
		border: 2rpx solid #00B894;
	}
	
	.action-btn.secondary {
		background: #EBF5FB;
		color: #3498DB;
		border: 2rpx solid #3498DB;
	}
	
	.action-btn.warning {
		background: #FFF9E6;
		color: #F39C12;
		border: 2rpx solid #F39C12;
	}
	
	.action-btn.break {
		background: #EFEBE9;
		color: #795548;
		border: 2rpx solid #795548;
	}
	
	.btn-emoji {
		font-size: 24rpx;
	}
	
	/* 下一题按钮 */
	.next-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12rpx;
		width: 80%;
		height: 96rpx;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		color: #FFF;
		border: none;
		border-radius: 48rpx;
		font-size: 34rpx;
		font-weight: bold;
		box-shadow: 0 8rpx 0 #C44A34, 0 12rpx 32rpx rgba(255, 159, 67, 0.3);
		transition: all 0.15s;
	}
	
	.next-btn:active {
		transform: translateY(6rpx);
		box-shadow: 0 2rpx 0 #C44A34;
	}
	
	.next-arrow {
		font-size: 32rpx;
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
	
	.loading-content {
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
		border: 6rpx solid rgba(255, 159, 67, 0.2);
		border-top-color: #FF9F43;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	
	.loading-text {
		font-size: 28rpx;
		color: #636E72;
	}

	/* ========== 动画定义 ========== */
	@keyframes bounce {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-16rpx); }
	}
	
	@keyframes pulse {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.08); }
	}
	
	@keyframes shake {
		0%, 100% { transform: translateX(0); }
		20% { transform: translateX(-12rpx); }
		40% { transform: translateX(12rpx); }
		60% { transform: translateX(-12rpx); }
		80% { transform: translateX(12rpx); }
	}
	
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(20rpx); }
		to { opacity: 1; transform: translateY(0); }
	}
	
	@keyframes glow {
		0%, 100% { box-shadow: 0 0 30rpx rgba(255, 107, 107, 0.4); }
		50% { box-shadow: 0 0 60rpx rgba(255, 107, 107, 0.8); }
	}
	
	@keyframes ripple {
		to { transform: scale(1.5); opacity: 0; }
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* ========== 响应式适配 ========== */
	@media screen and (max-width: 375px) {
		.hanzi-text {
			font-size: 100rpx;
		}
		
		.mic-button {
			width: 140rpx;
			height: 140rpx;
		}
		
		.mic-inner {
			width: 110rpx;
			height: 110rpx;
		}
	}
	
	@media screen and (min-width: 768px) {
		.word-card-wrapper {
			max-width: 600px;
			margin: 0 auto;
		}
		
		.bottom-controls {
			max-width: 600px;
			margin: 0 auto;
		}
	}
</style>
