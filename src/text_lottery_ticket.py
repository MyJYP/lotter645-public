"""
텍스트 기반 복권 용지 생성 (HTML/CSS)
이미지 파일 대신 텍스트로 7x7 그리드 렌더링
"""


def create_lottery_ticket_html(round_num, date, winning_numbers, bonus_number=None):
    """
    HTML/CSS로 복권 용지 생성

    Args:
        round_num: 회차 번호
        date: 날짜 (YYYY.MM.DD 형식)
        winning_numbers: 당첨번호 리스트 [n1, n2, n3, n4, n5, n6]
        bonus_number: 보너스 번호 (선택)

    Returns:
        str: HTML 코드
    """
    # 7x7 그리드 생성
    grid_html = ""
    number = 1

    for row in range(7):
        grid_html += '<div style="display:flex;">'
        for col in range(7):
            if number <= 45:
                # 번호가 당첨번호인지 확인
                is_winning = number in winning_numbers
                is_bonus = number == bonus_number

                # 스타일 결정
                if is_winning:
                    # 당첨번호 - 파란색 채움
                    cell_style = (
                        "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
                        "color: white;"
                        "font-weight: bold;"
                        "box-shadow: 0 2px 4px rgba(0,0,0,0.3);"
                    )
                elif is_bonus:
                    # 보너스 번호 - 금색 테두리
                    cell_style = (
                        "background: white;"
                        "color: #333;"
                        "border: 3px solid #FFD700;"
                        "font-weight: bold;"
                    )
                else:
                    # 일반 번호
                    cell_style = (
                        "background: white;"
                        "color: #333;"
                        "border: 1px solid #ddd;"
                    )

                grid_html += f'''
                <div style="
                    width: 60px;
                    height: 60px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 2px;
                    border-radius: 8px;
                    font-size: 20px;
                    {cell_style}
                ">
                    {number}
                </div>
                '''
                number += 1
            else:
                # 빈 칸
                grid_html += '''
                <div style="
                    width: 60px;
                    height: 60px;
                    margin: 2px;
                "></div>
                '''
        grid_html += '</div>'

    # 전체 HTML
    html = f'''
    <div style="
        background: white;
        border: 2px solid #ddd;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        max-width: 500px;
        margin: 10px auto;
    ">
        <!-- 헤더 -->
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        ">
            <div style="font-size: 24px; font-weight: bold;">A</div>
            <div style="font-size: 18px; margin-top: 5px;">제 {round_num}회</div>
        </div>

        <!-- 안내 텍스트 -->
        <div style="
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        ">
            아래 번호 중 6개를 선택하세요
        </div>

        <!-- 번호 그리드 -->
        <div style="margin: 20px 0;">
            {grid_html}
        </div>

        <!-- 하단 정보 -->
        <div style="
            border-top: 2px solid #eee;
            padding-top: 15px;
            margin-top: 20px;
        ">
            <div style="color: #333; font-size: 14px; margin-bottom: 8px;">
                <strong>추첨일:</strong> {date}
            </div>
            <div style="color: #667eea; font-size: 16px; font-weight: bold;">
                <strong>당첨번호:</strong> {', '.join(map(str, sorted(winning_numbers)))}
            </div>
            {f'<div style="color: #FFD700; font-size: 14px; margin-top: 5px;"><strong>보너스:</strong> {bonus_number}</div>' if bonus_number else ''}
        </div>
    </div>
    '''

    return html


def create_lottery_ticket_compact(round_num, date, winning_numbers, bonus_number=None):
    """
    컴팩트 버전 복권 용지 (작은 크기)

    Args:
        round_num: 회차 번호
        date: 날짜
        winning_numbers: 당첨번호 리스트
        bonus_number: 보너스 번호

    Returns:
        str: HTML 코드
    """
    # 7x7 그리드 생성 (작은 버전)
    grid_html = ""
    number = 1

    for row in range(7):
        grid_html += '<div style="display:flex; gap:1px;">'
        for col in range(7):
            if number <= 45:
                is_winning = number in winning_numbers

                if is_winning:
                    bg_color = "#667eea"
                    text_color = "white"
                else:
                    bg_color = "#f8f9fa"
                    text_color = "#333"

                grid_html += f'''
                <div style="
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: {bg_color};
                    color: {text_color};
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: {'bold' if is_winning else 'normal'};
                ">
                    {number}
                </div>
                '''
                number += 1
            else:
                grid_html += '<div style="width:32px;height:32px;"></div>'
        grid_html += '</div>'

    html = f'''
    <div style="
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px;
        margin: 5px;
        display: inline-block;
    ">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 8px; text-align: center;">
            {round_num}회 ({date})
        </div>
        {grid_html}
        <div style="font-size: 11px; color: #666; margin-top: 8px; text-align: center;">
            {', '.join(map(str, sorted(winning_numbers)))}
            {f' + {bonus_number}' if bonus_number else ''}
        </div>
    </div>
    '''

    return html


def create_lottery_grid_simple(winning_numbers):
    """
    매우 간단한 7x7 그리드 (웹 앱용)

    Args:
        winning_numbers: 당첨번호 리스트

    Returns:
        str: HTML 코드
    """
    grid_html = ""
    number = 1

    for row in range(7):
        grid_html += '<div style="display:flex; gap:3px; margin-bottom:3px;">'
        for col in range(7):
            if number <= 45:
                is_winning = number in winning_numbers

                if is_winning:
                    style = (
                        "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
                        "color: white; font-weight: bold;"
                        "box-shadow: 0 2px 4px rgba(102,126,234,0.4);"
                    )
                else:
                    style = (
                        "background: white; color: #666;"
                        "border: 1px solid #e0e0e0;"
                    )

                grid_html += f'''
                <div style="
                    width: 45px;
                    height: 45px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 6px;
                    font-size: 16px;
                    {style}
                ">
                    {number}
                </div>
                '''
                number += 1
            else:
                grid_html += '<div style="width:45px;height:45px;"></div>'
        grid_html += '</div>'

    return f'<div style="display:inline-block;">{grid_html}</div>'


if __name__ == "__main__":
    # 테스트
    print("\n" + "="*80)
    print("📝 텍스트 기반 복권 용지 생성 테스트")
    print("="*80)

    # 1204회차 테스트
    round_num = 1204
    date = "2025.12.27"
    winning_numbers = [8, 16, 28, 30, 31, 44]
    bonus_number = 27

    # HTML 생성
    html_full = create_lottery_ticket_html(round_num, date, winning_numbers, bonus_number)
    html_compact = create_lottery_ticket_compact(round_num, date, winning_numbers, bonus_number)
    html_simple = create_lottery_grid_simple(winning_numbers)

    # 파일로 저장 (테스트용)
    with open("../output/test_ticket_full.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>복권 용지 - {round_num}회</title>
        </head>
        <body style="background: #f5f5f5; padding: 20px; font-family: Arial, sans-serif;">
            <h2>전체 버전</h2>
            {html_full}

            <h2>컴팩트 버전</h2>
            {html_compact}

            <h2>심플 그리드</h2>
            {html_simple}
        </body>
        </html>
        """)

    print("\n✅ HTML 파일 생성 완료: output/test_ticket_full.html")
    print("\n💡 브라우저로 열어서 확인하세요!")
    print("   open output/test_ticket_full.html")
