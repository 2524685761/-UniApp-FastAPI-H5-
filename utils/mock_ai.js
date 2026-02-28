// 模拟AI服务：发音评分 + 情感识别
export default {
    // 模拟上传音频并分析
    analyzeAudio(filePath) {
        return new Promise((resolve) => {
            setTimeout(() => {
                // 随机生成模拟数据
                const score = Math.floor(Math.random() * 30) + 70; // 70-100分
                
                // 随机情绪状态
                const emotions = [
                    { type: 'neutral', label: '平静', tip: '保持专注，继续加油！' },
                    { type: 'happy', label: '自信', tip: '太棒了！你的状态非常好！' },
                    { type: 'confused', label: '困惑', tip: '这里有点难？让我们慢一点再试一次。' },
                    { type: 'frustrated', label: '挫败', tip: '别灰心，你已经很努力了，深呼吸一下。' }
                ];
                
                // 简单模拟：如果分数低，概率出现负面情绪
                let emotionIndex = 0;
                if (score < 80) {
                    emotionIndex = Math.random() > 0.5 ? 2 : 3;
                } else {
                    emotionIndex = Math.random() > 0.7 ? 1 : 0;
                }
                
                resolve({
                    score: score,
                    emotion: emotions[emotionIndex],
                    feedback: this.getFeedback(score, emotions[emotionIndex].type)
                });
            }, 1500); // 模拟网络延迟
        });
    },

    getFeedback(score, emotionType) {
        if (score >= 90) return "发音非常标准！像播音员一样！";
        if (score >= 80) return "发音不错，注意声调再准确一点哦。";
        if (emotionType === 'frustrated') return "没关系，这几个词确实有点难，我们拆开来读。";
        return "加油，多听几遍示范音，张大嘴巴再试一次。";
    }
}

