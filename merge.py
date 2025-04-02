import os
import subprocess
import glob

input_folder = "videos"
output_folder = "output_videos"
os.makedirs(output_folder, exist_ok=True)
#作品数
count = 3

# チャプター情報リスト
youtube_chapters = []
current_time = 0

def changeImageVideo(intro_img, intro_video, fade_filter):
    """
        画像を動画に変換
        パラメータ：-loop 1、-t 3 画像を3秒間「静止画」としてループ表示
    """
    subprocess.run(
        f"ffmpeg -loop 1 -t 3 -i {intro_img} -vf 'scale=1920:1080,{fade_filter}' "
        f"-c:v libx264 -pix_fmt yuv420p -y {intro_video}",
        shell=True
    )

def makeNoneAudio(intro_video, intro_with_audio):
    """
        空の音声ファイル(mp4)を作成
        -shortest(映像と音の長さを合わせる)
        -c:v copy -c:a aac(映像はコピー、音声はAAC形式にエンコード)
    """
    subprocess.run(
        f"ffmpeg -i {intro_video} -f lavfi -t 3 -i anullsrc=channel_layout=stereo:sample_rate=44100 "
        f"-shortest -c:v copy -c:a aac -pix_fmt yuv420p -y {intro_with_audio}",
        shell=True
    )

for i in range(1, count+1):
    #ID作成
    num = f"{i:03d}"

    """
        入力パスの設定
    """
    #作品紹介画像と総評画像のパス設定
    intro_img = f"{input_folder}/{num}_intro.jpeg"
    comment_img = f"{input_folder}/{num}_comment.jpeg"

    #プロジェクト動画のパス設定。movかmp4のどちらかを検索
    video_candidates = glob.glob(f"{input_folder}/{num}_project.*")
    project_video = None
    for v in video_candidates:
        if v.endswith(('.mp4', '.mov')):
            project_video = v
            break

    #動画と画像がない場合はスキップ
    if not (os.path.exists(intro_img) and os.path.exists(comment_img) and project_video):
        print(f"スキップ: {num} （データ不足）")
        continue

    """
        出力パスの設定
    """
    intro_video = f"{output_folder}/{num}_intro.mp4"
    comment_video = f"{output_folder}/{num}_comment.mp4"
    fixed_project_video = f"{output_folder}/{num}_project_fixed.mp4"
    output_video = f"{output_folder}/{num}_final.mp4"

    """
        動画作成
    """
    #フェードイン、アウトの設定(0秒から0.5秒でフェードイン、2.5秒から0.5秒でフェードアウト)
    fade_filter = "fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5,setsar=1"

    """
        画像→動画
        手順:①画像を動画に変換、②空のaudioを作成
    """
    #紹介画像を動画に変換
    changeImageVideo(intro_img, intro_video, fade_filter)
    # 無音の音声を作成して結合
    intro_with_audio = f"{output_folder}/{num}_intro_with_audio.mp4"
    #anullsrc(無音の音声)、
    makeNoneAudio(intro_video, intro_with_audio)

    #総評画像を動画に変換
    changeImageVideo(comment_img, comment_video, fade_filter)
    comment_with_audio = f"{output_folder}/{num}_comment_with_audio.mp4"
    makeNoneAudio(comment_video, comment_with_audio)

    """
        作品動画
        パラメータ:
            scale=1920:1080:force_original_aspect_ratio=decrease（元のアスペクト比を保ちつつ1920x1080以内にリサイズ）
            pad=1920:1080:(ow-iw)/2:(oh-ih)/2（余った部分は黒い余白でパディング）→強制アスペクトだと比が崩れるため。
    """
    # project動画をリサイズ
    subprocess.run(
        f"ffmpeg -i {project_video} "
        f"-vf 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1' "
        f"-r 30 -c:v libx264 -c:a aac -b:a 192k -pix_fmt yuv420p -y {fixed_project_video}",
        shell=True
    )

    """
        紹介画像+作品動画+総評画像の結合
    """
    # 音声付きconcat
    subprocess.run(
        f"ffmpeg -i {intro_with_audio} -i {fixed_project_video} -i {comment_with_audio} "
        f"-filter_complex \"[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]concat=n=3:v=1:a=1[outv][outa]\" "
        f"-map \"[outv]\" -map \"[outa]\" -c:v libx264 -c:a aac -pix_fmt yuv420p -y {output_video}",
        shell=True
    )

    print(f" {num} 完了")

    # 動画の長さを取得
    result = subprocess.run(
        f"ffprobe -i {output_video} -show_entries format=duration -v quiet -of csv='p=0'",
        shell=True, capture_output=True, text=True
    )
    duration = float(result.stdout.strip())

    # チャプター情報を追加
    youtube_chapters.append(f"{int(current_time // 60)}:{int(current_time % 60):02d} 生徒{i}")
    current_time += duration

print("個別動画の生成完了")

# 全体結合
final_output = "final_output.mp4"
with open("final_list.txt", "w") as f:
    for i in range(1, count+1):
        num = f"{i:03d}"
        f.write(f"file '{output_folder}/{num}_final.mp4'\n")

subprocess.run(f"ffmpeg -f concat -safe 0 -i final_list.txt -c copy {final_output}", shell=True)
print("全動画の結合完了")

# チャプター情報をファイルに保存
with open("youtube_chapters.txt", "w") as f:
    f.write("\n".join(youtube_chapters))
print("YouTube用チャプター情報を出力しました")
